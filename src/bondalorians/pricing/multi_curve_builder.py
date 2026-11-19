from __future__ import annotations

from pathlib import Path

import QuantLib as ql
import pandas as pd

DATES = ["2026-10-30", "2026-11-11"]
TENORS = [1, 2, 3, 5, 7, 10, 15, 20, 30]


def ql_date(value: str) -> ql.Date:
    y, m, d = map(int, value.split("-"))
    return ql.Date(d, m, y)


def build_curves(date_str: str):
    valuation_date = ql_date(date_str)
    ql.Settings.instance().evaluationDate = valuation_date

    calendar = ql.TARGET()
    day_count = ql.Actual365Fixed()

    shift = 0.0005 if date_str == DATES[1] else 0.0

    ois_quotes = {
        t: 0.021 + 0.00035 * min(t, 10) + shift
        for t in TENORS
    }

    # Instruments OIS courts : cotations synthétiques.
    short_ois_quotes = [
        ("1W", ql.Period(1, ql.Weeks), 0.021 + 0.00035 * 7 / 365 + shift),
        ("1M", ql.Period(1, ql.Months), 0.021 + 0.00035 / 12 + shift),
        ("3M", ql.Period(3, ql.Months), 0.021 + 0.00035 * 0.25 + shift),
        ("6M", ql.Period(6, ql.Months), 0.021 + 0.00035 * 0.5 + shift),
    ]

    swap_quotes = {
        t: ois_quotes[t] + 0.0020 + 0.00004 * min(t, 10)
        for t in TENORS
    }

    # Courbe d'actualisation €STR
    estr = ql.Estr()
    short_ois_helpers = [
        ql.OISRateHelper(
            2,
            period,
            ql.QuoteHandle(ql.SimpleQuote(rate)),
            estr,
        )
        for _, period, rate in short_ois_quotes
    ]

    long_ois_helpers = [
        ql.OISRateHelper(
            2,
            ql.Period(t, ql.Years),
            ql.QuoteHandle(ql.SimpleQuote(rate)),
            estr,
        )
        for t, rate in ois_quotes.items()
    ]

    ois_helpers = short_ois_helpers + long_ois_helpers

    discount_curve = ql.PiecewiseLogLinearDiscount(
        valuation_date, ois_helpers, day_count
    )
    discount_curve.enableExtrapolation()
    discount_handle = ql.YieldTermStructureHandle(discount_curve)

    # Courbe de projection EURIBOR 6M, actualisée avec €STR
    projection_handle = ql.RelinkableYieldTermStructureHandle()
    euribor6m = ql.Euribor6M(projection_handle)

    # Dépôt EURIBOR 6M : ancrage court de la courbe de projection.
    euribor6m_deposit_rate = (
        ois_quotes[1] + 0.0020 - 0.00035 * 0.5
    )
    deposit_helper = ql.DepositRateHelper(
        ql.QuoteHandle(ql.SimpleQuote(euribor6m_deposit_rate)),
        ql.Period(6, ql.Months),
        2,
        calendar,
        ql.ModifiedFollowing,
        False,
        ql.Actual360(),
    )

    swap_helpers = [
        ql.SwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(rate)),
            ql.Period(t, ql.Years),
            calendar,
            ql.Annual,
            ql.ModifiedFollowing,
            ql.Thirty360(ql.Thirty360.European),
            euribor6m,
            ql.QuoteHandle(),
            ql.Period(0, ql.Days),
            discount_handle,
        )
        for t, rate in swap_quotes.items()
    ]

    projection_helpers = [deposit_helper] + swap_helpers

    projection_curve = ql.PiecewiseLogLinearDiscount(
        valuation_date, projection_helpers, day_count
    )
    projection_curve.enableExtrapolation()

    # Déclencher le bootstrap avant de relier le handle.
    projection_curve.discount(
        calendar.advance(valuation_date, ql.Period(30, ql.Years))
    )
    projection_handle.linkTo(projection_curve)

    errors = []

    for (label, _, rate), helper in zip(
        short_ois_quotes, short_ois_helpers
    ):
        errors.append((
            "ESTR_OIS",
            label,
            (helper.impliedQuote() - rate) * 10000,
        ))

    for t, helper in zip(TENORS, long_ois_helpers):
        errors.append((
            "ESTR_OIS",
            t,
            (helper.impliedQuote() - ois_quotes[t]) * 10000,
        ))

    errors.append((
        "EURIBOR6M_DEPOSIT",
        "6M",
        (deposit_helper.impliedQuote() - euribor6m_deposit_rate) * 10000,
    ))

    # Revalorisation indépendante des swaps EURIBOR 6M.
    for t, helper in zip(TENORS, swap_helpers):
        swap = helper.swap()
        swap.setPricingEngine(
            ql.DiscountingSwapEngine(discount_handle)
        )
        swap.recalculate()

        fair_rate = swap.fairRate()
        repricing_error = (fair_rate - swap_quotes[t]) * 10000

        errors.append((
            "EURIBOR6M_SWAP_REPRICING",
            t,
            repricing_error,
        ))


    rows = []
    for t in TENORS:
        maturity = calendar.advance(
            valuation_date, ql.Period(t, ql.Years)
        )
        for name, curve in [
            ("ESTR_OIS_DISCOUNT", discount_curve),
            ("EURIBOR6M_PROJECTION", projection_curve),
        ]:
            rows.append({
                "valuation_date": date_str,
                "curve_name": name,
                "tenor_years": t,
                "discount_factor": curve.discount(maturity),
                "zero_rate_pct": (
                    curve.zeroRate(
                        maturity, day_count, ql.Continuous
                    ).rate() * 100
                ),
                "source": "SYNTHETIC",
                "synthetic": True,
            })

    quotes = [
        {
            "valuation_date": date_str,
            "instrument": "ESTR_OIS",
            "tenor": label,
            "par_rate_pct": rate * 100,
            "source": "SYNTHETIC",
            "synthetic": True,
        }
        for label, _, rate in short_ois_quotes
    ]

    quotes.append({
        "valuation_date": date_str,
        "instrument": "EURIBOR6M_DEPOSIT",
        "tenor": "6M",
        "par_rate_pct": euribor6m_deposit_rate * 100,
        "source": "SYNTHETIC",
        "synthetic": True,
    })

    for name, values in [
        ("ESTR_OIS", ois_quotes),
        ("EURIBOR6M_SWAP", swap_quotes),
    ]:
        for t, rate in values.items():
            quotes.append({
                "valuation_date": date_str,
                "instrument": name,
                "tenor_years": t,
                "par_rate_pct": rate * 100,
                "source": "SYNTHETIC",
                "synthetic": True,
            })

    # Forwards EURIBOR 6M calculés directement par QuantLib.
    forward_rows = []
    spot_date = euribor6m.valueDate(valuation_date)

    period_start = spot_date

    for i in range(10):
        period_end = euribor6m.maturityDate(period_start)

        forward_rate = projection_curve.forwardRate(
            period_start,
            period_end,
            euribor6m.dayCounter(),
            ql.Simple,
        ).rate()

        forward_rows.append({
            "valuation_date": date_str,
            "period_start": period_start.ISO(),
            "period_end": period_end.ISO(),
            "forward_euribor6m_pct": forward_rate * 100,
            "ois_df_start": discount_curve.discount(period_start),
            "ois_df_end": discount_curve.discount(period_end),
            "source": "SYNTHETIC",
            "synthetic": True,
        })

        period_start = period_end

    return rows, quotes, errors, forward_rows


def main():
    output = Path("data/market/synthetic")
    output.mkdir(parents=True, exist_ok=True)

    all_curves, all_quotes, all_forwards = [], [], []

    for date in DATES:
        curves, quotes, errors, forwards = build_curves(date)

        max_error = max(abs(e[2]) for e in errors)
        print(f"{date}: erreur maximale = {max_error:.8f} bp")
        assert max_error < 0.01, "Échec de calibration"

        all_curves.extend(curves)
        all_quotes.extend(quotes)
        all_forwards.extend(forwards)

    pd.DataFrame(all_curves).to_csv(
        output / "multi_curves.csv", index=False
    )
    pd.DataFrame(all_quotes).to_csv(
        output / "market_quotes.csv", index=False
    )
    pd.DataFrame(all_forwards).to_csv(
        output / "euribor6m_forwards.csv", index=False
    )

    print("Courbes, cotations et forwards enregistrés.")
    print(f"Points de courbe : {len(all_curves)}")
    print(f"Cotations : {len(all_quotes)}")
    print(f"Forwards 6M : {len(all_forwards)}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market"
OUT.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://data-api.ecb.europa.eu/service/data/YC"
START_DATE = "2026-10-29"
END_DATE = "2026-11-12"
TARGET_DATES = {"2026-10-30", "2026-11-11"}

TENORS = ["3M", "6M", "9M"] + [f"{n}Y" for n in range(1, 31)]
CURVE_TYPES = {
    "AAA": "G_N_A",
    "ALL": "G_N_C",
}


def fetch_one(curve_label: str, instrument: str, tenor: str) -> list[dict]:
    key = f"B.U2.EUR.4F.{instrument}.SV_C_YM.SR_{tenor}"
    params = urlencode({
        "startPeriod": START_DATE,
        "endPeriod": END_DATE,
        "format": "csvdata",
    })
    url = f"{BASE_URL}/{key}?{params}"
    request = Request(url, headers={"User-Agent": "Bondalorians-Hackathon/1.0"})

    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                content = response.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            rows = []
            for item in reader:
                date = item.get("TIME_PERIOD")
                value = item.get("OBS_VALUE")
                if date in TARGET_DATES and value not in (None, "", "NaN"):
                    rows.append({
                        "valuation_date": date,
                        "curve_type": curve_label,
                        "curve_name": f"ECB_EURO_AREA_{curve_label}_SPOT",
                        "tenor": tenor,
                        "tenor_years": (
                            float(tenor[:-1]) / 12 if tenor.endswith("M")
                            else float(tenor[:-1])
                        ),
                        "zero_rate_pct": float(value),
                        "compounding": "CONTINUOUS",
                        "source": "ECB",
                        "source_series": key,
                        "synthetic": False,
                    })
            return rows
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == 2:
                print(f"ERREUR {key}: {exc}")
                return []
            time.sleep(2 ** attempt)
    return []


tasks = []
with ThreadPoolExecutor(max_workers=8) as pool:
    for label, instrument in CURVE_TYPES.items():
        for tenor in TENORS:
            tasks.append(pool.submit(fetch_one, label, instrument, tenor))

    results = []
    for future in as_completed(tasks):
        results.extend(future.result())

if not results:
    raise SystemExit(
        "Aucune observation BCE récupérée. Vérifier l'accès réseau et les séries SDMX."
    )

df = pd.DataFrame(results).sort_values(
    ["curve_type", "valuation_date", "tenor_years"]
)

raw_path = OUT / "ecb_zero_curves_raw.csv"
df.to_csv(raw_path, index=False)

print("\n=== COURBES BCE RECUPEREES ===")
print("Observations :", len(df))
print("Fichier :", raw_path)

for curve in sorted(df.curve_type.unique()):
    for date in sorted(df.valuation_date.unique()):
        subset = df[
            (df.curve_type == curve) &
            (df.valuation_date == date)
        ]
        if not subset.empty:
            print(
                f"{curve} | {date} | {len(subset)} maturités | "
                f"{subset.tenor_years.min():g}Y à {subset.tenor_years.max():g}Y"
            )

print("\n=== DATES CIBLES ===")
for date in sorted(TARGET_DATES):
    count = len(df[df.valuation_date == date])
    print(f"{date}: {count} observations")

missing = TARGET_DATES - set(df.valuation_date.unique())
if missing:
    print("\nATTENTION - dates absentes :", sorted(missing))
    print("Ne pas remplacer silencieusement ces dates par une autre date.")

print("\n=== APERCU ===")
print(df.head(12).to_string(index=False))

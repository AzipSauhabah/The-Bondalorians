# The Bondalorians — Comparable Bond Pricing Agent

A runnable local prototype for the CDC Asset Management Hackathon use case 3. It demonstrates a Streamlit UI, a LangGraph workflow, transparent comparable ranking, a deterministic bond-pricing engine, and optional persistence to PostgreSQL.

> **Important:** all included bond observations and the EUR curve are synthetic demonstration data. This is not a production pricer, market data feed, CDC tool, Murex integration, BlackRock integration, investment recommendation, or tradable quote.

## 1. Requirements

- macOS (Apple Silicon or Intel)
- Python 3.11 or 3.12
- Git
- Optional: Docker Desktop (for PostgreSQL)

## 2. Run locally on a Mac

```bash
cd bondalorians
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
streamlit run app/Home.py
```

Streamlit will open in your browser, usually at http://localhost:8501. Select the target bond in the sidebar and click **Lancer le pricing**.

## 3. Run tests

```bash
pytest -q
```

## 4. Use PostgreSQL with Docker (optional)

The app defaults to SQLite so it runs immediately without Docker. To use PostgreSQL:

```bash
docker compose up -d db
```

Edit `.env` and set:

```dotenv
DATABASE_URL=postgresql+psycopg://bondalorians:bondalorians@localhost:5432/bondalorians
```

Restart Streamlit. Pricing runs will be written to the `pricing_runs` table. Stop PostgreSQL with `docker compose down`.

## 5. Project structure

```text
bondalorians/
├── app/Home.py                       # Streamlit UI
├── data/comparable_bonds.csv         # Synthetic bond universe
├── src/bondalorians/
│   ├── agent/graph.py                # LangGraph workflow
│   ├── data/repository.py            # Local data access
│   ├── integrations/mcp_adapter.py   # Replaceable MCP boundary (demo adapter)
│   ├── matching/engine.py            # Hard filters + similarity ranking
│   ├── pricing/engine.py              # YTM, spread and cashflow valuation
│   ├── db.py                          # SQLite/PostgreSQL audit persistence
│   └── models.py                      # Request model
├── tests/
├── docker-compose.yml
└── pyproject.toml
```

## 6. Current workflow

1. Streamlit collects target bond characteristics.
2. LangGraph retrieves the available bond universe through an adapter.
3. Matching applies hard filters (currency and seniority) and weighted soft scoring (maturity, coupon, rating, sector, issuer group, optionality, ESG).
4. The pricing engine estimates each comparable's yield to maturity from its clean price, computes a simple maturity-interpolated risk-free proxy and derives a weighted credit spread.
5. The target yield is converted into a clean price by discounting semiannual coupon cashflows.
6. The app displays the panel, rationale, spread, price range and indicative confidence, and attempts to persist the run.

## 7. What is deliberately not implemented yet

These are extension points for the hackathon, not claims of existing integration:

- Official CDC MCP clients and actual Murex / BlackRock tool calls.
- Mistral LLM calls and LangGraph tool-calling agent.
- Vector RAG and Graph RAG.
- Official market curves, conventions, calendars, accrued interest and complex embedded-option valuation.
- Calibrated ML model and out-of-time backtesting.
- Authentication and production security.

The local `DemoMarketDataAdapter` is intentionally isolated. Once the CDC MCP documentation and credentials are available, implement a new adapter with the same `search_bonds()` contract, or evolve it into typed MCP tool calls. Keep pricing deterministic and separate from LLM-generated explanations.

## 8. Before publishing to GitHub

Create an empty GitHub repository named `bondalorians`, then from this directory:

```bash
git init
git add .
git commit -m "Initial Bondalorians bond pricing prototype"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/bondalorians.git
git push -u origin main
```

Do not commit `.env`, API keys, credentials, CDC data, or private MCP documentation.

## 9. Important quantitative limitations

This is a hackathon architecture spike, not a validated fixed-income valuation library. The illustrative curve is a simple interpolated par/yield proxy, the matching weights are hand-set, the spread aggregation is a weighted average, and the pricing routine assumes regular semiannual fixed coupons. It does not handle day-count conventions, business-day calendars, stubs, amortization, floating-rate coupons, calls/puts, credit recovery, liquidity calibration, accrued interest or option-adjusted spreads. Those must be specified and tested against the CDC dataset and business conventions before relying on prices.

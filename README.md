# FoodShield

Full-stack simulation and decision-support platform that models how natural disruptors (drought, flooding, extreme heat, pest swarms, frost) impact food production, projects food insecurity, and recommends pre-emptive aid allocation.

## Architecture

```
ingestion/   → pulls NASA FIRMS, FEWS NET, FAO GIEWS, GDACS, World Bank
db/          → PostgreSQL + PostGIS + TimescaleDB schema
simulator/   → geospatial impact + ML projection (3/6/12mo)
optimizer/   → MILP food-aid allocation with logistics constraints
api/         → FastAPI service exposing simulator, projector, optimizer
agent/       → continuous alert monitor over live feeds
web/         → Next.js + Mapbox dashboard
infra/       → docker-compose, deploy configs
```

## Quick start

```bash
cp .env.example .env       # then fill in API keys
docker compose -f infra/docker-compose.yml up -d
# api:  http://localhost:8000/docs
# web:  http://localhost:3000
```

## API keys to request

| Source | Where |
|---|---|
| NASA FIRMS | https://firms.modaps.eosdis.nasa.gov/api/map_key/ |
| FAO GIEWS | https://fpma.fao.org/ (public, but rate-limited) |
| FEWS NET | https://fews.net/data — no key, shapefile download |
| GDACS | https://www.gdacs.org/xml/rss.xml — public |
| World Bank | https://data.worldbank.org/ — public API |
| Mapbox | https://account.mapbox.com/access-tokens/ |

## Run locally without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make train        # trains XGBoost quantile projectors → models/
make test         # 19 unit tests covering simulator, projector, allocator, API, ingestion
make backtest     # writes docs/backtest_2017_somalia.md
```

## Models & validation

The projector is **three XGBoost quantile regressors per horizon** (3/6/12 mo, quantiles 0.10/0.50/0.90), giving point estimates with calibrated CI bands. Training corpus is currently a physics-calibrated synthetic dataset (see `simulator/train_projector.py`) — swap to FEWS NET-labelled rows once `ipc_observations` is populated. Validation MAE on held-out regions: 0.12 phases @ 3mo → 0.30 phases @ 12mo. See `docs/backtest_2017_somalia.md` for a worked historical case.

## Allocator

PuLP MILP with a **vulnerability-weighted objective**: priority_weight(r) = 1 + 2·poverty + 1.5·impact + 1·{r ∈ priority_groups}. Honors depot stock, regional demand, total tonnage, total budget, and (when toggled) drops regions intersecting `conflict_zones` before solving.

## Build status

- [x] Week 1–2 — data infra
- [x] Week 3–4 — simulator + map UI
- [x] Week 5–6 — projection model (XGBoost quantile, synthetic corpus → FEWS NET pending)
- [x] Week 7–8 — allocation optimizer (vulnerability-weighted MILP)
- [x] Week 9 — dashboard + policy export (CSV via `POST /export/policy`)
- [~] Week 10 — validation + demo (Somalia 2017 backtest done; full holdout pending FEWS NET ingest)

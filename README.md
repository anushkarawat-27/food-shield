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

## Build status

- [x] Week 1–2 — data infra
- [ ] Week 3–4 — simulator + map UI
- [ ] Week 5–6 — projection model
- [ ] Week 7–8 — allocation optimizer
- [ ] Week 9 — dashboard + policy export
- [ ] Week 10 — validation + demo

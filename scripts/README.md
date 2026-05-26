# scripts/

Operational scripts. Most run inside the API container (`make api` → bash, or `docker compose exec api ...`); a few are local-friendly.

## Bootstrap order

Run once after `make up` so the simulator/optimizer have real demographic + crop data to operate on:

```bash
docker compose exec api python -m scripts.seed_regions        # country polygons from Natural Earth
docker compose exec api python -m scripts.update_populations  # POP_EST per country
docker compose exec api python -m scripts.update_poverty      # World Bank SI.POV.DDAY
docker compose exec api python -m scripts.seed_crops          # FAO-derived crop calendars + portfolios
docker compose exec api python -m ingestion.sources.fewsnet   # IPC labels (uses bundled fixture if offline)
docker compose exec api python -m ingestion.run_all           # FIRMS / GDACS / GIEWS / WorldBank events
```

Order matters — each step assumes the previous one ran:

| Script | Reads | Writes | Idempotent? |
|---|---|---|---|
| `seed_regions.py` | Natural Earth GeoJSON (HTTP) | `regions` (admin_level=0) | yes (ON CONFLICT DO NOTHING) |
| `update_populations.py` | Natural Earth POP_EST | `regions.population` | yes (UPDATE) |
| `update_poverty.py` | World Bank `SI.POV.DDAY` | `regions.poverty_pct`; default 5% for missing | yes |
| `seed_crops.py` | embedded FAO crop-calendar tables | `crop_calendar`, `region_crops` | yes |
| `ingestion/sources/fewsnet.py` | FEWS NET GeoJSON (or `FEWSNET_GEOJSON_URL`, or local fixture) | `ipc_observations` | yes (ON CONFLICT update) |
| `ingestion/run_all.py` | live RSS / APIs | `disruptor_events` | append-only |

## Modeling

```bash
python -m simulator.train_projector   # XGBoost quantile models → models/
python -m scripts.backtest            # writes docs/backtest_2017_somalia.md
python -m scripts.demo                # full offline end-to-end demo (no DB needed)
```

## Operational

```bash
python -m agent.monitor               # one polling pass (or Prefect flow when scheduled)
scripts/demo.sh                       # curl-based demo against a running API
```

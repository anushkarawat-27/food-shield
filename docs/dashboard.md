# Dashboard

Next.js 14 (App Router) + Mapbox GL + Tailwind. Source under `web/`.

## Component map

```
app/page.tsx               ← root, renders <Dashboard/>
components/Dashboard.tsx   ← layout shell, debounced /simulate on scenario change
  ├─ WorldMap.tsx          ← Mapbox map; choropleth of yield_delta_pct per region
  ├─ Legend.tsx            ← color scale for yield-loss severity
  └─ RegionPanel.tsx       ← right sidebar
       ├─ disruptor sliders (drought / flood / heat / pest / frost)
       ├─ ProjectionPanel.tsx  ← /project results, 3/6/12mo CI bands
       └─ AllocationPanel.tsx  ← /recommend MILP solve + "Export policy CSV"
lib/api.ts                 ← typed fetch wrappers for every endpoint
lib/store.ts               ← Zustand store: scenario, impacts, selectedRegion
```

## Required env vars

| Var | Purpose | Where to get it |
|---|---|---|
| `NEXT_PUBLIC_MAPBOX_TOKEN` | base map tiles | https://account.mapbox.com/access-tokens/ |
| `NEXT_PUBLIC_API_URL` | API base (defaults to `http://localhost:8000`) | self |

Without the Mapbox token `WorldMap.tsx` returns an empty container instead of crashing — the rest of the dashboard still works.

## How it ties to the backend

| UI action | Endpoint | Backend module |
|---|---|---|
| Click region → adjust sliders | _no call_ | local Zustand state |
| Slider change (debounced 250ms) | `POST /simulate` | `simulator/impact.py` |
| "Run projection" | `POST /project` | `simulator/projector.py` (loads `models/`) |
| "Run allocation" | `POST /recommend` | `optimizer/allocator.py` |
| "Export policy CSV" | `POST /export/policy` | `api/routes/export.py` |

## Demo flow (for graders)

1. `make up` then wait for the API healthcheck.
2. Browse to http://localhost:3000.
3. Click Somalia → drag drought slider to 0.9, heat to 0.7.
4. Watch the choropleth darken; right panel populates with affected population.
5. Click **Run projection** → IPC CI bands appear for 3/6/12 mo.
6. Click **Run allocation** → MILP solution appears with priority-weighted shipments.
7. Click **Export policy CSV** → browser downloads the recommended allocation.

For a non-interactive demo run `python -m scripts.demo` (uses the FastAPI TestClient + mocked DB — no infra required).

## Known limitations

- No live alert-feed subscription yet (`agent/monitor.py` writes to Redis pubsub `foodshield:alerts`, but the dashboard doesn't subscribe — wire with a SSE/websocket bridge in the API to surface them).
- Region selection currently keys off admin-0 (countries); admin-1 selection works once `seed_regions.py` is extended with GADM admin-1 polygons.
- Screenshot intentionally not committed — capture one yourself by running the demo flow above. Drop it at `docs/dashboard_screenshot.png` and the README will pick it up if a future update references it.

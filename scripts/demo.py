"""End-to-end FoodShield demo — runs offline, no Postgres required.

Builds a small in-memory cursor that satisfies every query the API issues for
a 3-region scenario, spins up the FastAPI app via TestClient, then walks
through simulate → project → recommend → export, pretty-printing each step.

This is what graders / new contributors should run first to see the system
work end-to-end:

    python -m scripts.demo

For a *live* API instance, run scripts/demo.sh instead — same flow via curl.
"""
from __future__ import annotations

import contextlib
import json
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Fake cursor — same idea as tests/conftest.FakeCursor, copied here so the
# script has zero dev-deps beyond what the API already needs.
# ---------------------------------------------------------------------------
class _FakeCursor:
    def __init__(self, scripts: dict[str, list[dict]]):
        self._scripts = {k.lower(): v for k, v in scripts.items()}
        self._last: list[dict] = []

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        sql_l = sql.lower()
        match = max((k for k in self._scripts if k in sql_l), key=len, default=None)
        self._last = list(self._scripts.get(match, []))

    def fetchall(self) -> list[dict]:
        return self._last

    def fetchone(self) -> dict | None:
        return self._last[0] if self._last else None


DEMO_DATA: dict[str, list[dict]] = {
    # impact.simulate_scenario — region demographics
    "as population": [
        {"id": 101, "population": 850_000, "poverty_pct": 76.0},   # Bay, Somalia
        {"id": 102, "population": 720_000, "poverty_pct": 82.0},   # Bakool, Somalia
        {"id": 201, "population": 1_200_000, "poverty_pct": 35.0}, # Turkana, Kenya
    ],
    "from region_crops": [],  # fallback heuristic path keeps the demo simple
    # allocator._fetch_region_meta
    "name, iso3, coalesce": [
        {"id": 101, "name": "Bay",       "iso3": "SOM", "poverty_pct": 76.0},
        {"id": 102, "name": "Bakool",    "iso3": "SOM", "poverty_pct": 82.0},
        {"id": 201, "name": "Turkana",   "iso3": "KEN", "poverty_pct": 35.0},
    ],
    # allocator._fetch_depots
    "from depots": [
        {"id": 1, "name": "Mombasa_Port",   "stock_tonnes": 8_000.0},
        {"id": 2, "name": "Djibouti_Port",  "stock_tonnes": 5_000.0},
    ],
    # allocator._conflict_region_ids — none for this demo
    "conflict_zones": [],
    # export._region_lookup
    "select id, name, iso3 from regions": [
        {"id": 101, "name": "Bay",     "iso3": "SOM"},
        {"id": 102, "name": "Bakool",  "iso3": "SOM"},
        {"id": 201, "name": "Turkana", "iso3": "KEN"},
    ],
}

SCENARIO = {
    101: {"drought": 0.90, "heat": 0.75},
    102: {"drought": 0.92, "heat": 0.72},
    201: {"drought": 0.70, "heat": 0.55, "pest": 0.30},
}


def _patch_db():
    fc = _FakeCursor(DEMO_DATA)

    @contextlib.contextmanager
    def fake_cm():
        yield fc

    import api.db
    import simulator.impact
    import optimizer.allocator
    import api.routes.export
    import agent.monitor
    for mod in (api.db, simulator.impact, optimizer.allocator,
                api.routes.export, agent.monitor):
        mod.cursor = fake_cm

    import simulator.projector
    simulator.projector._poverty_lookup = lambda ids: {
        r["id"]: r["poverty_pct"] for r in DEMO_DATA["as population"]
    }


def _hr(title: str) -> None:
    bar = "─" * 78
    print(f"\n{bar}\n  {title}\n{bar}")


def main() -> None:
    _patch_db()

    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)

    _hr("1) /health — liveness")
    print(client.get("/health").json())

    _hr("2) /simulate — current-period yield loss + affected pop")
    sim_resp = client.post("/simulate", json={"scenario": SCENARIO}).json()
    for row in sim_resp:
        print(f"  region={row['region_id']:>4}  "
              f"yield_delta={row['yield_delta_pct']:>+7.2f}%  "
              f"affected≈{row['affected_population']:>9,}")

    _hr("3) /project — IPC phase forecast at 3 / 6 / 12 months")
    proj_resp = client.post(
        "/project",
        json={"scenario": SCENARIO, "horizons_months": [3, 6, 12]},
    ).json()
    for row in proj_resp:
        print(f"  region={row['region_id']:>4}  h={row['horizon_months']:>2}mo  "
              f"IPC={row['ipc_phase']:.2f}  "
              f"CI=[{row['ci_low']:.2f}, {row['ci_high']:.2f}]")

    _hr("4) /recommend — vulnerability-weighted aid allocation MILP")
    rec_body = {
        "scenario": SCENARIO,
        "total_tonnage": 10_000,
        "total_budget_usd": 5_000_000,
        "priority_population_groups": ["SOM"],   # boost Somalia regions
        "avoid_conflict_zones": True,
    }
    rec_resp = client.post("/recommend", json=rec_body).json()
    print(f"  delivered_tonnes={sum(a['tonnes'] for a in rec_resp['allocations']):,.1f}")
    print(f"  total_cost=${rec_resp['total_cost_usd']:,.0f}")
    print(f"  unmet_demand={rec_resp['unmet_demand_tonnes']:,.1f} t")
    print(f"  objective={rec_resp.get('objective_value')}")
    print(f"  skipped_conflict_regions={rec_resp.get('skipped_conflict_regions')}")
    print("  allocations:")
    for a in rec_resp["allocations"]:
        print(f"    region={a['region_id']:>4}  "
              f"{a['tonnes']:>7,.0f} t from {a['from_depot']:<14} "
              f"cover={a['coverage_pct']:>5.1f}%  w={a.get('priority_weight'):.2f}")

    _hr("5) /export/policy — downloadable CSV (first 6 lines)")
    csv = client.post("/export/policy", json=rec_body).text
    for line in csv.splitlines()[:6]:
        print("  " + line)
    print(f"  ... ({len(csv.splitlines())} lines total)")

    _hr("done")
    print("Live curl flow: scripts/demo.sh (assumes API running on :8000)")


if __name__ == "__main__":
    main()

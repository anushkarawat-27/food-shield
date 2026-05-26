"""End-to-end smoke tests against the FastAPI app."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_simulate_endpoint(fake_cursor):
    fake_cursor(
        {
            "as population": [
                {"id": 1, "population": 500_000, "poverty_pct": 30.0},
            ],
            "from region_crops": [],
        }
    )
    client = TestClient(app)
    r = client.post("/simulate", json={"scenario": {"1": {"drought": 0.7}}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list) and len(body) == 1
    assert body[0]["region_id"] == 1


def test_project_endpoint(fake_cursor):
    fake_cursor({"as population": [{"id": 1, "population": 0, "poverty_pct": 30.0}]})
    client = TestClient(app)
    r = client.post(
        "/project",
        json={"scenario": {"1": {"drought": 0.7}}, "horizons_months": [3, 12]},
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert {row["horizon_months"] for row in rows} == {3, 12}


def test_recommend_endpoint(fake_cursor):
    fake_cursor(
        {
            "as population": [
                {"id": 1, "population": 500_000, "poverty_pct": 50.0},
            ],
            "from region_crops": [],
            "name, iso3": [
                {"id": 1, "name": "r1", "iso3": "AAA", "poverty_pct": 50.0},
            ],
            "from depots": [{"id": 1, "name": "d", "stock_tonnes": 200.0}],
            "conflict_zones": [],
        }
    )
    client = TestClient(app)
    r = client.post(
        "/recommend",
        json={
            "scenario": {"1": {"drought": 0.8}},
            "total_tonnage": 150,
            "total_budget_usd": 100_000,
            "priority_population_groups": [],
            "avoid_conflict_zones": False,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "allocations" in body
    assert body["total_cost_usd"] <= 100_000.0 + 1e-3

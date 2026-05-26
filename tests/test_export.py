"""Test the policy CSV export endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_export_policy_returns_csv(fake_cursor):
    fake_cursor(
        {
            "as population": [
                {"id": 1, "population": 500_000, "poverty_pct": 50.0},
            ],
            "from region_crops": [],
            "name, iso3, coalesce": [
                {"id": 1, "name": "TestRegion", "iso3": "TST", "poverty_pct": 50.0},
            ],
            "from depots": [{"id": 1, "name": "central", "stock_tonnes": 500.0}],
            "conflict_zones": [],
            # export.py _region_lookup query
            "select id, name, iso3 from regions": [
                {"id": 1, "name": "TestRegion", "iso3": "TST"},
            ],
        }
    )
    client = TestClient(app)
    r = client.post(
        "/export/policy",
        json={
            "scenario": {"1": {"drought": 0.8}},
            "total_tonnage": 150,
            "total_budget_usd": 100_000,
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    body = r.text
    assert "region_id,region_name" in body
    assert "TestRegion" in body
    assert "TOTAL_TONNES" in body
    assert "UNMET_DEMAND_TONNES" in body

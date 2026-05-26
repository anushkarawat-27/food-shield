"""Tests for the food-aid allocation MILP."""
from __future__ import annotations

from optimizer.allocator import recommend_allocation


def _setup(fake_cursor):
    return fake_cursor(
        {
            # impact.simulate_scenario region query (selects ... AS population)
            "as population": [
                {"id": 1, "population": 1_000_000, "poverty_pct": 80.0},
                {"id": 2, "population": 1_000_000, "poverty_pct": 10.0},
            ],
            "from region_crops": [],
            # allocator._fetch_region_meta
            "name, iso3": [
                {"id": 1, "name": "high_poverty", "iso3": "AAA", "poverty_pct": 80.0},
                {"id": 2, "name": "low_poverty",  "iso3": "BBB", "poverty_pct": 10.0},
            ],
            # allocator._fetch_depots
            "from depots": [
                {"id": 1, "name": "central_depot", "stock_tonnes": 500.0},
            ],
            # allocator._conflict_region_ids
            "conflict_zones": [],
        }
    )


def test_respects_depot_stock_and_total_tonnage(fake_cursor):
    _setup(fake_cursor)
    res = recommend_allocation(
        scenario={1: {"drought": 0.9}, 2: {"drought": 0.9}},
        total_tonnage=400.0,
        total_budget_usd=1_000_000.0,
        priority_groups=[],
        avoid_conflict_zones=False,
    )
    total = sum(a["tonnes"] for a in res["allocations"])
    assert total <= 400.0 + 1e-3
    assert total <= 500.0 + 1e-3


def test_respects_budget(fake_cursor):
    _setup(fake_cursor)
    res = recommend_allocation(
        scenario={1: {"drought": 0.9}, 2: {"drought": 0.9}},
        total_tonnage=5_000.0,
        total_budget_usd=40_000.0,
        priority_groups=[],
        avoid_conflict_zones=False,
    )
    assert res["total_cost_usd"] <= 40_000.0 + 1e-3
    assert sum(a["tonnes"] for a in res["allocations"]) <= 200.0 + 1e-3


def test_weighted_objective_favors_high_poverty(fake_cursor):
    _setup(fake_cursor)
    res = recommend_allocation(
        scenario={1: {"drought": 0.9}, 2: {"drought": 0.9}},
        total_tonnage=10_000.0,
        total_budget_usd=10_000_000.0,
        priority_groups=[],
        avoid_conflict_zones=False,
    )
    by_region = {a["region_id"]: a for a in res["allocations"]}
    assert by_region[1]["priority_weight"] > by_region[2]["priority_weight"]


def test_empty_scenario(fake_cursor):
    fake_cursor({})
    res = recommend_allocation(
        scenario={},
        total_tonnage=100.0,
        total_budget_usd=10_000.0,
        priority_groups=[],
        avoid_conflict_zones=False,
    )
    assert res["allocations"] == []
    assert res["total_cost_usd"] == 0.0

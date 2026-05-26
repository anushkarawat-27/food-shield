"""Tests for the crop-aware impact simulator."""
from __future__ import annotations

from simulator.impact import simulate_scenario


def test_empty_scenario_returns_empty(fake_cursor):
    fake_cursor({})
    assert simulate_scenario({}) == []


def test_yield_delta_clamped_and_signed(fake_cursor):
    fake_cursor(
        {
            "as population": [
                {"id": 1, "population": 1_000_000, "poverty_pct": 40.0},
            ],
            "from region_crops": [],  # no crop portfolio → fallback heuristic
        }
    )
    out = simulate_scenario({1: {"drought": 1.0, "heat": 1.0}})
    assert len(out) == 1
    r = out[0]
    assert r["region_id"] == 1
    assert -95.0 <= r["yield_delta_pct"] <= 0.0
    assert r["affected_population"] >= 0


def test_higher_severity_means_larger_loss(fake_cursor):
    fake_cursor(
        {
            "as population": [
                {"id": 1, "population": 1_000_000, "poverty_pct": 40.0},
            ],
            "from region_crops": [],
        }
    )
    light = simulate_scenario({1: {"drought": 0.1}})[0]
    heavy = simulate_scenario({1: {"drought": 0.9}})[0]
    assert heavy["yield_delta_pct"] <= light["yield_delta_pct"]
    assert heavy["affected_population"] >= light["affected_population"]


def test_crop_portfolio_path(fake_cursor):
    fake_cursor(
        {
            "as population": [
                {"id": 7, "population": 500_000, "poverty_pct": 50.0},
            ],
            "from region_crops": [
                {
                    "region_id": 7, "crop": "maize", "share": 1.0,
                    "plant_start": 1, "plant_end": 30,
                    "harvest_start": 300, "harvest_end": 360,
                },
            ],
        }
    )
    out = simulate_scenario({7: {"drought": 0.8}})
    assert out[0]["yield_delta_pct"] <= 0.0

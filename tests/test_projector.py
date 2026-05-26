"""Tests for the projection model (uses trained joblib models when present)."""
from __future__ import annotations

from simulator.projector import project_scenario


def test_phase_in_ipc_range_and_ci_ordered(fake_cursor):
    fake_cursor({"from regions": [{"id": 1, "poverty_pct": 40.0}]})
    out = project_scenario({1: {"drought": 0.7, "heat": 0.4}}, horizons=[3, 6, 12])
    assert len(out) == 3
    for r in out:
        assert 1.0 <= r["ci_low"] <= r["ipc_phase"] <= r["ci_high"] <= 5.0
        assert r["horizon_months"] in (3, 6, 12)


def test_ci_widens_with_horizon(fake_cursor):
    fake_cursor({"from regions": [{"id": 1, "poverty_pct": 40.0}]})
    out = project_scenario({1: {"drought": 0.5}}, horizons=[3, 12])
    by_h = {r["horizon_months"]: r for r in out}
    band_3 = by_h[3]["ci_high"] - by_h[3]["ci_low"]
    band_12 = by_h[12]["ci_high"] - by_h[12]["ci_low"]
    assert band_12 >= band_3, "12-month CI should be at least as wide as 3-month"


def test_more_disruption_means_higher_phase(fake_cursor):
    fake_cursor({"from regions": [{"id": 1, "poverty_pct": 40.0}]})
    calm = project_scenario({1: {"drought": 0.0}}, horizons=[6])[0]
    crisis = project_scenario({1: {"drought": 0.95, "heat": 0.9}}, horizons=[6])[0]
    assert crisis["ipc_phase"] >= calm["ipc_phase"]

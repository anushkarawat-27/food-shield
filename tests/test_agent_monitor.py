"""Tests for the continuous alert agent's polling logic."""
from __future__ import annotations

from agent.monitor import run_once, _weighted_score


def test_weighted_score_monotonic():
    low = _weighted_score({"drought": 0.1})
    high = _weighted_score({"drought": 0.9})
    assert high > low


def test_run_once_fires_alert_above_threshold(fake_cursor):
    cur = fake_cursor(
        {
            # _per_region_severity
            "max(e.severity) as sev": [
                {"region_id": 1, "disruptor_type": "drought", "sev": 0.95},
                {"region_id": 1, "disruptor_type": "heat",    "sev": 0.80},
                {"region_id": 2, "disruptor_type": "flood",   "sev": 0.10},
            ],
            # _open_alert_region_ids
            "from alerts where resolved_at": [],
            # projector reads regions for poverty
            "as population": [{"id": 1, "poverty_pct": 60.0}, {"id": 2, "poverty_pct": 20.0}],
            "select id, coalesce(poverty_pct": [
                {"id": 1, "poverty_pct": 60.0}, {"id": 2, "poverty_pct": 20.0}
            ],
            # the alert insert — FakeCursor swallows it; we just check 'fired'
            "insert into alerts": [],
        }
    )
    result = run_once()
    assert result["polled"] == 2
    assert result["fired"] >= 1, "region 1 should trip the score threshold"


def test_run_once_skips_open_alert_regions(fake_cursor):
    fake_cursor(
        {
            "max(e.severity) as sev": [
                {"region_id": 9, "disruptor_type": "drought", "sev": 0.99},
            ],
            "from alerts where resolved_at": [{"region_id": 9}],
            "as population": [{"id": 9, "poverty_pct": 60.0}],
            "select id, coalesce(poverty_pct": [{"id": 9, "poverty_pct": 60.0}],
            "insert into alerts": [],
        }
    )
    result = run_once()
    assert result["fired"] == 0
    assert result["skipped_open"] == 1


def test_run_once_empty(fake_cursor):
    fake_cursor({"max(e.severity) as sev": []})
    result = run_once()
    assert result == {"polled": 0, "fired": 0, "skipped_open": 0}

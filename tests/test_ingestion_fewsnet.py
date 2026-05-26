"""Unit tests for FEWS NET ingestor — runs offline against the bundled fixture."""
from __future__ import annotations

from datetime import date

from ingestion.sources.fewsnet import FewsNetIngestor, FIXTURE_PATH


def test_fixture_loads():
    payload = FewsNetIngestor().fetch()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) >= 5


def test_normalize_valid_feature():
    feat = {
        "type": "Feature",
        "properties": {
            "country": "Somalia",
            "admin": "Bay",
            "ipc_phase": 4,
            "period_kind": "CS",
            "period_start": "2017-06-01",
            "period_end": "2017-09-30",
        },
        "geometry": {"type": "Point", "coordinates": [44, 3]},
    }
    obs = FewsNetIngestor.normalize(feat)
    assert obs is not None
    assert obs.ipc_phase == 4
    assert obs.period_kind == "CS"
    assert obs.period_start == date(2017, 6, 1)
    assert obs.country == "Somalia"


def test_normalize_rejects_invalid():
    # missing phase
    assert FewsNetIngestor.normalize({"properties": {}, "geometry": {"type": "Point", "coordinates": [0, 0]}}) is None
    # phase out of range
    bad = {
        "properties": {"ipc_phase": 9, "period_start": "2017-01-01"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }
    assert FewsNetIngestor.normalize(bad) is None
    # missing geometry
    assert FewsNetIngestor.normalize({"properties": {"ipc_phase": 3, "period_start": "2017-01-01"}}) is None


def test_fixture_features_all_normalize():
    payload = FewsNetIngestor().fetch()
    parsed = [FewsNetIngestor.normalize(f) for f in payload["features"]]
    assert all(p is not None for p in parsed), "every bundled fixture feature should be valid"
    phases = {p.ipc_phase for p in parsed}
    assert phases.issubset({1, 2, 3, 4, 5})

"""Unit test for the GDACS ingestor's normalize() — runs offline."""
from __future__ import annotations

from datetime import datetime

from ingestion.sources.gdacs import GdacsIngestor


def test_normalize_drought_red():
    sample = {
        "gdacs_eventtype": "DR",
        "georss_point": "-1.286389 36.817223",  # Nairobi
        "gdacs_alertlevel": "Red",
        "gdacs_fromdate": "2026-01-15 00:00:00",
        "gdacs_todate": "2026-02-15 00:00:00",
        "gdacs_eventid": "drought_2026_01_kenya",
    }
    ev = GdacsIngestor().normalize(sample)
    assert ev is not None
    assert ev.disruptor_type == "drought"
    assert ev.severity == 0.9
    assert "POINT(36.817223 -1.286389)" == ev.geom_wkt
    assert isinstance(ev.started_at, datetime)


def test_normalize_skips_unknown_type():
    sample = {
        "gdacs_eventtype": "EQ",  # earthquake — not in scope
        "georss_point": "0 0",
        "gdacs_alertlevel": "Red",
    }
    assert GdacsIngestor().normalize(sample) is None


def test_normalize_skips_missing_geom():
    sample = {
        "gdacs_eventtype": "DR",
        "gdacs_alertlevel": "Orange",
    }
    assert GdacsIngestor().normalize(sample) is None

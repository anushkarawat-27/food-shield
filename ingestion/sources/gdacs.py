"""GDACS global disaster alerts. Public RSS/GeoJSON feed, no API key required.

Feed: https://www.gdacs.org/xml/rss.xml
GDACS event types mapped to FoodShield disruptor codes; non-mapped events skipped.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import feedparser

from ingestion.base import DisruptorEvent, Ingestor

FEED_URL = "https://www.gdacs.org/xml/rss.xml"

# GDACS event types we care about. EQ/TC/VO (earthquake/cyclone/volcano) not in scope.
GDACS_TYPE_MAP = {
    "DR": "drought",
    "FL": "flood",
    "TC": "flood",      # tropical cyclones drive flooding
    "WF": "heat",       # wildfire used as a heat-stress proxy
}

# GDACS alert level → 0..1 severity
ALERT_LEVEL_SEVERITY = {"Green": 0.2, "Orange": 0.6, "Red": 0.9}


class GdacsIngestor(Ingestor):
    source = "gdacs"

    def fetch(self) -> Iterable[Any]:
        parsed = feedparser.parse(FEED_URL)
        return parsed.entries

    def normalize(self, raw: Any) -> DisruptorEvent | None:
        ev_type_code = raw.get("gdacs_eventtype")
        disruptor = GDACS_TYPE_MAP.get(ev_type_code)
        if disruptor is None:
            return None

        # Coords come as "lat lon" in GeoRSS point
        point = raw.get("georss_point")
        if not point:
            return None
        try:
            lat_s, lon_s = point.split()
            lat, lon = float(lat_s), float(lon_s)
        except ValueError:
            return None

        alert = raw.get("gdacs_alertlevel", "Green")
        severity = ALERT_LEVEL_SEVERITY.get(alert, 0.2)

        started = raw.get("gdacs_fromdate") or raw.get("published")
        started_dt = _parse_dt(started) or datetime.now(timezone.utc)
        ended_dt = _parse_dt(raw.get("gdacs_todate"))

        return DisruptorEvent(
            source=self.source,
            source_event_id=raw.get("gdacs_eventid"),
            disruptor_type=disruptor,
            severity=severity,
            geom_wkt=f"POINT({lon} {lat})",
            started_at=started_dt,
            ended_at=ended_dt,
            raw={k: v for k, v in raw.items() if isinstance(v, (str, int, float, bool))},
        )


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


if __name__ == "__main__":
    n = GdacsIngestor().run()
    print(f"gdacs: inserted {n} events")

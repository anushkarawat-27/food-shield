"""NASA FIRMS — active fire detections (used as heat/drought stress proxy).

Requires a MAP_KEY: https://firms.modaps.eosdis.nasa.gov/api/map_key/
CSV endpoint:
  https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{area}/{day_range}
"""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from typing import Any, Iterable

import requests

from ingestion.base import DisruptorEvent, Ingestor


class FirmsIngestor(Ingestor):
    source = "firms"

    def __init__(self, area: str = "world", day_range: int = 1, sensor: str = "VIIRS_SNPP_NRT"):
        self.area = area
        self.day_range = day_range
        self.sensor = sensor

    def fetch(self) -> Iterable[Any]:
        key = os.environ.get("NASA_FIRMS_MAP_KEY")
        if not key:
            return []
        url = (
            "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{key}/{self.sensor}/{self.area}/{self.day_range}"
        )
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        yield from reader

    def normalize(self, raw: Any) -> DisruptorEvent | None:
        try:
            lat = float(raw["latitude"])
            lon = float(raw["longitude"])
            frp = float(raw.get("frp", 0))                 # fire radiative power
        except (KeyError, ValueError):
            return None
        # Map FRP to 0..1 severity (cap at 100 MW)
        severity = min(frp / 100.0, 1.0)
        acq_date = raw.get("acq_date", "")
        acq_time = raw.get("acq_time", "0000").zfill(4)
        try:
            started = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            started = datetime.now(timezone.utc)
        return DisruptorEvent(
            source=self.source,
            source_event_id=None,
            disruptor_type="heat",
            severity=severity,
            geom_wkt=f"POINT({lon} {lat})",
            started_at=started,
            raw=raw,
        )


if __name__ == "__main__":
    n = FirmsIngestor().run()
    print(f"firms: inserted {n} events")

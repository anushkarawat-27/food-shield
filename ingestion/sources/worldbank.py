"""World Bank — population and poverty indicators per country.

API: https://api.worldbank.org/v2/country/all/indicator/{INDICATOR}?format=json
Indicators:
  SP.POP.TOTL    — total population
  SI.POV.NAHC    — poverty headcount ratio at national poverty lines (%)

Loads into regions.population and regions.poverty_pct at admin_level=0.
Stubbed until Week 2 — depends on regions table being seeded from GADM first.
"""
from __future__ import annotations

from typing import Any, Iterable

import requests

from ingestion.base import DisruptorEvent, Ingestor

BASE = "https://api.worldbank.org/v2"


class WorldBankIngestor(Ingestor):
    source = "worldbank"

    def fetch(self) -> Iterable[Any]:
        return []

    def normalize(self, raw: Any) -> DisruptorEvent | None:
        return None

    def sync_population(self) -> int:
        """Pull SP.POP.TOTL for all countries (latest year), update regions."""
        url = f"{BASE}/country/all/indicator/SP.POP.TOTL?format=json&per_page=500&date=2023"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        payload = r.json()
        if len(payload) < 2:
            return 0
        # TODO Week 2: UPSERT into regions where iso3 = country.id and admin_level = 0
        return len(payload[1])


if __name__ == "__main__":
    print("worldbank: stub — implement population/poverty sync in Week 2")

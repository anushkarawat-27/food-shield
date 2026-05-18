"""FEWS NET — IPC food insecurity classifications by region.

Data: https://fews.net/data — shapefiles, no API key.
Use the current-period IPC shapefile; load polygons + phase (1..5) into projections
as ground-truth labels for model training (Week 5-6 work).

This module's run() is a placeholder until the shapefile pipeline is wired in
during Week 5. It does not insert disruptor_events — FEWS NET output is a
target/label, not an upstream disruptor.
"""
from __future__ import annotations

from typing import Any, Iterable

from ingestion.base import DisruptorEvent, Ingestor


class FewsNetIngestor(Ingestor):
    source = "fewsnet"

    def fetch(self) -> Iterable[Any]:
        return []

    def normalize(self, raw: Any) -> DisruptorEvent | None:
        return None


if __name__ == "__main__":
    print("fewsnet: stub — implement shapefile loader in Week 5")

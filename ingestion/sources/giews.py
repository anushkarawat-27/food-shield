"""FAO GIEWS — crop production briefs and food prices.

Country briefs: https://www.fao.org/giews/countrybrief/
FPMA price data: https://fpma.fao.org/giews/fpmat4/

Output is written to food_price_baseline (commodity prices) and used to adjust
disruptor severity by overlaying production-shortfall flags. Stubbed until Week 2.
"""
from __future__ import annotations

from typing import Any, Iterable

from ingestion.base import DisruptorEvent, Ingestor


class GiewsIngestor(Ingestor):
    source = "giews"

    def fetch(self) -> Iterable[Any]:
        return []

    def normalize(self, raw: Any) -> DisruptorEvent | None:
        return None


if __name__ == "__main__":
    print("giews: stub — implement FPMA price scrape in Week 2")

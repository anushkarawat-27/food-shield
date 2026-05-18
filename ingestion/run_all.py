"""Run all ingestors sequentially. Wire into Prefect later for scheduling."""
from __future__ import annotations

from ingestion.sources.firms import FirmsIngestor
from ingestion.sources.gdacs import GdacsIngestor
from ingestion.sources.giews import GiewsIngestor
from ingestion.sources.worldbank import WorldBankIngestor

INGESTORS = [GdacsIngestor(), FirmsIngestor(), GiewsIngestor(), WorldBankIngestor()]


def main() -> None:
    for ing in INGESTORS:
        try:
            n = ing.run()
            print(f"{ing.source}: {n}")
        except Exception as e:  # noqa: BLE001
            print(f"{ing.source}: FAILED — {e}")


if __name__ == "__main__":
    main()

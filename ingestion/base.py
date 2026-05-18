from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

import psycopg
from psycopg.types.json import Jsonb


@dataclass
class DisruptorEvent:
    source: str
    source_event_id: str | None
    disruptor_type: str            # 'drought' | 'flood' | 'heat' | 'pest' | 'frost'
    severity: float                # 0..1
    geom_wkt: str                  # WGS84
    started_at: datetime
    ended_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def get_conn() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


class Ingestor(ABC):
    """Subclasses implement fetch() and normalize(); base handles upsert."""

    source: str = "unknown"

    @abstractmethod
    def fetch(self) -> Iterable[Any]:
        ...

    @abstractmethod
    def normalize(self, raw: Any) -> DisruptorEvent | None:
        ...

    def run(self) -> int:
        inserted = 0
        with get_conn() as conn, conn.cursor() as cur:
            for raw in self.fetch():
                ev = self.normalize(raw)
                if ev is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO disruptor_events
                        (source, source_event_id, disruptor_type, severity,
                         geom, started_at, ended_at, raw)
                    VALUES (%s, %s, %s, %s,
                            ST_GeomFromText(%s, 4326), %s, %s, %s)
                    """,
                    (
                        ev.source,
                        ev.source_event_id,
                        ev.disruptor_type,
                        ev.severity,
                        ev.geom_wkt,
                        ev.started_at,
                        ev.ended_at,
                        Jsonb(ev.raw),
                    ),
                )
                inserted += 1
            conn.commit()
        return inserted

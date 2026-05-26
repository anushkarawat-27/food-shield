"""FEWS NET — IPC food-insecurity classifications by region.

Unlike disruptor sources (FIRMS, GDACS, …), FEWS NET output is a *label*, not
an upstream disruptor — so this ingestor doesn't conform to the DisruptorEvent
Ingestor interface. It writes to a separate `ipc_observations` table that the
projector trainer reads as supervised targets.

Fetch order:
  1. If FEWSNET_GEOJSON_URL is set in the env, GET that URL.
  2. Otherwise load the bundled fixture (Horn-of-Africa 2017) — guarantees the
     pipeline runs offline and in CI.

Spatial join: each FEWS NET polygon is matched to every `regions` row whose
geometry intersects it, and (region_id, period_kind, period_start) is upserted
into ipc_observations.

Run:  python -m ingestion.sources.fewsnet
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import requests

DEFAULT_TIMEOUT_S = 15
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "fewsnet_sample.geojson"


@dataclass
class IpcObservation:
    period_kind: str          # CS / ML1 / ML2
    period_start: date
    period_end: date | None
    ipc_phase: int            # 1..5
    geom_geojson: dict        # GeoJSON geometry (dict)
    country: str
    admin: str


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


class FewsNetIngestor:
    source = "fewsnet"

    def __init__(self, geojson_url: str | None = None):
        # Caller-supplied URL > env var > fixture
        self.geojson_url = geojson_url or os.environ.get("FEWSNET_GEOJSON_URL")

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def fetch(self) -> dict:
        if self.geojson_url:
            try:
                r = requests.get(self.geojson_url, timeout=DEFAULT_TIMEOUT_S)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                print(f"[fewsnet] live fetch failed ({e}); using fixture", flush=True)
        return json.loads(FIXTURE_PATH.read_text())

    # ------------------------------------------------------------------
    # Normalize a single GeoJSON feature → IpcObservation
    # ------------------------------------------------------------------
    @staticmethod
    def normalize(feature: dict) -> IpcObservation | None:
        props = feature.get("properties") or {}
        try:
            phase = int(props["ipc_phase"])
        except (KeyError, ValueError, TypeError):
            return None
        if not (1 <= phase <= 5):
            return None
        start = _parse_date(props.get("period_start"))
        if start is None:
            return None
        geom = feature.get("geometry")
        if not geom:
            return None
        return IpcObservation(
            period_kind=str(props.get("period_kind") or "CS"),
            period_start=start,
            period_end=_parse_date(props.get("period_end")),
            ipc_phase=phase,
            geom_geojson=geom,
            country=str(props.get("country") or ""),
            admin=str(props.get("admin") or ""),
        )

    # ------------------------------------------------------------------
    # Persist: spatial-join to regions, upsert ipc_observations
    # ------------------------------------------------------------------
    def run(self) -> dict:
        """Returns counts for logging: {features, matched, upserted, skipped}."""
        from ingestion.base import get_conn  # imports psycopg lazily

        payload = self.fetch()
        features = payload.get("features") or []
        observations = [o for o in (self.normalize(f) for f in features) if o is not None]

        upserted = 0
        matched_regions = 0
        skipped_no_region = 0

        with get_conn() as conn, conn.cursor() as cur:
            for obs in observations:
                geom_str = json.dumps(obs.geom_geojson)
                # Find every region whose geometry intersects the FEWS NET polygon.
                cur.execute(
                    """
                    SELECT id FROM regions
                    WHERE ST_Intersects(geom, ST_GeomFromGeoJSON(%s))
                    """,
                    (geom_str,),
                )
                region_ids = [row[0] for row in cur.fetchall()]
                if not region_ids:
                    skipped_no_region += 1
                    continue
                matched_regions += len(region_ids)
                for rid in region_ids:
                    cur.execute(
                        """
                        INSERT INTO ipc_observations
                            (region_id, period_kind, period_start, period_end, ipc_phase, source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (region_id, period_kind, period_start)
                        DO UPDATE SET ipc_phase = EXCLUDED.ipc_phase,
                                      period_end = EXCLUDED.period_end,
                                      ingested_at = NOW()
                        """,
                        (
                            rid,
                            obs.period_kind,
                            obs.period_start,
                            obs.period_end,
                            obs.ipc_phase,
                            self.source,
                        ),
                    )
                    upserted += 1
            conn.commit()

        return {
            "features": len(features),
            "observations": len(observations),
            "matched_regions": matched_regions,
            "upserted": upserted,
            "skipped_no_region": skipped_no_region,
        }


if __name__ == "__main__":
    stats = FewsNetIngestor().run()
    print(f"fewsnet: {stats}")

from fastapi import APIRouter

from api.db import cursor

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/geojson")
def events_geojson(days: int = 30, limit: int = 1000) -> dict:
    """Recent disruptor events as a GeoJSON FeatureCollection for map overlay."""
    with cursor() as cur:
        cur.execute(
            """
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(feature), '[]'::json)
            ) AS fc
            FROM (
                SELECT json_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(geom)::json,
                    'properties', json_build_object(
                        'id', id,
                        'source', source,
                        'disruptor_type', disruptor_type,
                        'severity', severity,
                        'started_at', started_at
                    )
                ) AS feature
                FROM disruptor_events
                WHERE started_at >= NOW() - (%s || ' days')::interval
                ORDER BY started_at DESC
                LIMIT %s
            ) f
            """,
            (str(days), limit),
        )
        row = cur.fetchone()
    return row["fc"] if row else {"type": "FeatureCollection", "features": []}


@router.get("/summary")
def events_summary(days: int = 30) -> list[dict]:
    with cursor() as cur:
        cur.execute(
            """
            SELECT disruptor_type, COUNT(*)::int AS n,
                   AVG(severity)::real AS avg_severity
            FROM disruptor_events
            WHERE started_at >= NOW() - (%s || ' days')::interval
            GROUP BY disruptor_type
            ORDER BY n DESC
            """,
            (str(days),),
        )
        return list(cur.fetchall())

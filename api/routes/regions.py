from fastapi import APIRouter

from api.db import cursor

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("")
def list_regions(admin_level: int = 0, iso3: str | None = None) -> list[dict]:
    sql = """
        SELECT id, iso3, admin_level, name, population, poverty_pct,
               ST_AsGeoJSON(centroid) AS centroid
        FROM regions
        WHERE admin_level = %s
    """
    args: list = [admin_level]
    if iso3:
        sql += " AND iso3 = %s"
        args.append(iso3)
    sql += " ORDER BY name"
    with cursor() as cur:
        cur.execute(sql, args)
        return list(cur.fetchall())


@router.get("/geojson")
def regions_geojson(admin_level: int = 0) -> dict:
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
                    'id', id,
                    'geometry', ST_AsGeoJSON(geom)::json,
                    'properties', json_build_object(
                        'iso3', iso3,
                        'name', name,
                        'population', population,
                        'poverty_pct', poverty_pct
                    )
                ) AS feature
                FROM regions WHERE admin_level = %s
            ) f
            """,
            (admin_level,),
        )
        row = cur.fetchone()
    return row["fc"] if row else {"type": "FeatureCollection", "features": []}

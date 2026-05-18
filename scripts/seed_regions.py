"""Seed the regions table with country polygons from Natural Earth admin-0.

Source: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/
Pulls the GeoJSON mirror on GitHub so no manual download is needed.
"""
from __future__ import annotations

import json

import requests
from psycopg.types.json import Jsonb

from api.db import cursor

URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)


def main() -> None:
    print(f"Fetching {URL} ...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    fc = r.json()
    features = fc["features"]
    print(f"Got {len(features)} country features. Upserting...")

    with cursor() as cur:
        for f in features:
            props = f["properties"]
            iso3 = props.get("ADM0_A3") or props.get("ISO_A3")
            name = props.get("NAME") or props.get("ADMIN")
            if not iso3 or not name:
                continue
            geom = json.dumps(f["geometry"])
            cur.execute(
                """
                INSERT INTO regions (iso3, admin_level, name, geom, centroid)
                VALUES (
                    %s, 0, %s,
                    ST_Multi(ST_GeomFromGeoJSON(%s)),
                    ST_Centroid(ST_GeomFromGeoJSON(%s))
                )
                ON CONFLICT DO NOTHING
                """,
                (iso3, name, geom, geom),
            )
    print("Done.")


if __name__ == "__main__":
    main()

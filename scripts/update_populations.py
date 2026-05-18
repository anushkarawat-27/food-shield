"""Backfill regions.population using Natural Earth's POP_EST field.

Run after seed_regions.py to give the simulator/optimizer real demand numbers.
Idempotent — re-running just overwrites with the latest estimates.
"""
from __future__ import annotations

import requests

from api.db import cursor

URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)


def main() -> None:
    print(f"Fetching {URL} ...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    features = r.json()["features"]
    print(f"Got {len(features)} countries. Updating populations...")

    updated = 0
    with cursor() as cur:
        for f in features:
            props = f["properties"]
            iso3 = props.get("ADM0_A3") or props.get("ISO_A3")
            pop = props.get("POP_EST")
            if not iso3 or not pop:
                continue
            cur.execute(
                """
                UPDATE regions
                SET population = %s
                WHERE iso3 = %s AND admin_level = 0
                """,
                (int(pop), iso3),
            )
            updated += cur.rowcount
    print(f"Updated {updated} rows.")


if __name__ == "__main__":
    main()

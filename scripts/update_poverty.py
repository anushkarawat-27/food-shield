"""Backfill regions.poverty_pct from the World Bank Open Data API.

Indicator: SI.POV.DDAY — Poverty headcount ratio at $2.15/day (2017 PPP) (% of population).
For each country we pick the most recent non-null observation (the WB only
publishes this every few years per country, so we walk back in time).

API: https://api.worldbank.org/v2/country/all/indicator/SI.POV.DDAY?format=json
Public, no key required.

Run after seed_regions.py. Idempotent.
"""
from __future__ import annotations

import requests

from api.db import cursor

INDICATOR = "SI.POV.DDAY"
URL = (
    f"https://api.worldbank.org/v2/country/all/indicator/{INDICATOR}"
    "?format=json&per_page=20000"
)


def main() -> None:
    print(f"Fetching {URL} ...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    payload = r.json()
    if len(payload) < 2 or payload[1] is None:
        print("Unexpected payload shape from World Bank.")
        return

    records = payload[1]
    print(f"Got {len(records)} observations across all years/countries.")

    # Keep most-recent non-null value per iso3.
    latest: dict[str, tuple[int, float]] = {}
    for rec in records:
        iso3 = rec.get("countryiso3code")
        value = rec.get("value")
        year_str = rec.get("date")
        if not iso3 or value is None or not year_str:
            continue
        try:
            year = int(year_str)
        except ValueError:
            continue
        prev = latest.get(iso3)
        if prev is None or year > prev[0]:
            latest[iso3] = (year, float(value))

    print(f"Resolved latest poverty rate for {len(latest)} countries.")

    updated = 0
    with cursor() as cur:
        for iso3, (year, pct) in latest.items():
            cur.execute(
                """
                UPDATE regions
                SET poverty_pct = %s
                WHERE iso3 = %s AND admin_level = 0
                """,
                (pct, iso3),
            )
            updated += cur.rowcount

    # Anything still NULL after the WB pass gets a conservative fallback so the
    # impact model has a sane default (used for high-income / no-data countries).
    with cursor() as cur:
        cur.execute(
            "UPDATE regions SET poverty_pct = 5.0 WHERE poverty_pct IS NULL AND admin_level = 0",
        )
        filled_default = cur.rowcount

    print(f"Updated {updated} rows from World Bank; defaulted {filled_default} remaining rows to 5%.")


if __name__ == "__main__":
    main()

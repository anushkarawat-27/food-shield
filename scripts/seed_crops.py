"""Seed crop_calendar + region_crops for major producing countries.

Data: simplified from FAOSTAT top producers. Crop shares are approximate and
intended for demo realism, not policy. Crop calendars come from FAO GIEWS
country crop calendar averages, encoded by hemisphere.

Run after seed_regions.py and update_populations.py.
"""
from __future__ import annotations

from api.db import cursor

# Day-of-year windows for each crop by hemisphere ("N" = northern, "S" = southern,
# "T" = tropical/year-round). Numbers are approximate FAO crop calendar midpoints.
CROP_CALENDAR = {
    "wheat": {
        "N": {"plant_start": 244, "plant_end": 334, "harvest_start": 152, "harvest_end": 244},  # Sep–Nov plant, Jun–Aug harvest
        "S": {"plant_start": 91,  "plant_end": 181, "harvest_start": 305, "harvest_end": 31},   # Apr–Jun plant, Nov–Jan harvest
    },
    "maize": {
        "N": {"plant_start": 91,  "plant_end": 181, "harvest_start": 244, "harvest_end": 334},  # Apr–Jun plant, Sep–Nov harvest
        "S": {"plant_start": 274, "plant_end": 365, "harvest_start": 60,  "harvest_end": 152},  # Oct–Dec plant, Mar–May harvest
        "T": {"plant_start": 60,  "plant_end": 152, "harvest_start": 213, "harvest_end": 305},  # main season
    },
    "rice": {
        "N": {"plant_start": 121, "plant_end": 213, "harvest_start": 244, "harvest_end": 335},
        "T": {"plant_start": 60,  "plant_end": 273, "harvest_start": 152, "harvest_end": 365},  # multi-season
    },
    "sorghum": {
        "N": {"plant_start": 121, "plant_end": 196, "harvest_start": 244, "harvest_end": 335},
        "S": {"plant_start": 305, "plant_end": 31,  "harvest_start": 60,  "harvest_end": 152},
        "T": {"plant_start": 152, "plant_end": 243, "harvest_start": 304, "harvest_end": 31},
    },
    "cassava": {
        "T": {"plant_start": 60,  "plant_end": 152, "harvest_start": 244, "harvest_end": 121},  # ~9-12mo cycle
    },
}

# Approximate top producers + share (within their own portfolio, not global).
# Numbers reflect rough crop mix per country (sum ≈ 1.0).
REGION_CROPS: dict[str, list[tuple[str, float]]] = {
    # Wheat-heavy
    "USA": [("wheat", 0.20), ("maize", 0.55), ("sorghum", 0.10), ("rice", 0.05)],
    "CHN": [("rice", 0.40), ("wheat", 0.30), ("maize", 0.25)],
    "IND": [("rice", 0.40), ("wheat", 0.30), ("sorghum", 0.10), ("maize", 0.10)],
    "RUS": [("wheat", 0.60), ("maize", 0.20)],
    "FRA": [("wheat", 0.50), ("maize", 0.30)],
    "CAN": [("wheat", 0.55), ("maize", 0.20)],
    "AUS": [("wheat", 0.55), ("sorghum", 0.10)],
    "UKR": [("wheat", 0.45), ("maize", 0.40)],
    "DEU": [("wheat", 0.50), ("maize", 0.25)],
    "GBR": [("wheat", 0.55)],
    "TUR": [("wheat", 0.55), ("maize", 0.15)],
    "ARG": [("wheat", 0.20), ("maize", 0.40), ("sorghum", 0.10)],
    "BRA": [("maize", 0.40), ("rice", 0.10), ("cassava", 0.20)],
    "MEX": [("maize", 0.55), ("wheat", 0.10), ("sorghum", 0.15)],
    "EGY": [("wheat", 0.35), ("rice", 0.25), ("maize", 0.25)],
    "PAK": [("wheat", 0.45), ("rice", 0.20), ("maize", 0.15)],
    "IRN": [("wheat", 0.55), ("rice", 0.15)],
    "KAZ": [("wheat", 0.70)],
    # Rice-heavy
    "IDN": [("rice", 0.55), ("maize", 0.20), ("cassava", 0.15)],
    "BGD": [("rice", 0.75), ("wheat", 0.10)],
    "VNM": [("rice", 0.70), ("maize", 0.15), ("cassava", 0.10)],
    "THA": [("rice", 0.55), ("cassava", 0.15), ("maize", 0.15)],
    "PHL": [("rice", 0.60), ("maize", 0.20)],
    "MMR": [("rice", 0.70)],
    "JPN": [("rice", 0.70), ("wheat", 0.10)],
    "KHM": [("rice", 0.75)],
    "LAO": [("rice", 0.70)],
    # Africa / sorghum / cassava
    "NGA": [("cassava", 0.35), ("sorghum", 0.25), ("maize", 0.20), ("rice", 0.10)],
    "ETH": [("maize", 0.25), ("sorghum", 0.30), ("wheat", 0.20)],
    "KEN": [("maize", 0.55), ("wheat", 0.10), ("sorghum", 0.10)],
    "TZA": [("maize", 0.45), ("cassava", 0.20), ("rice", 0.10), ("sorghum", 0.10)],
    "UGA": [("maize", 0.30), ("cassava", 0.25), ("sorghum", 0.15)],
    "GHA": [("cassava", 0.35), ("maize", 0.25), ("sorghum", 0.10), ("rice", 0.10)],
    "COD": [("cassava", 0.55), ("maize", 0.20), ("rice", 0.10)],
    "AGO": [("cassava", 0.50), ("maize", 0.25)],
    "SDN": [("sorghum", 0.55), ("wheat", 0.15)],
    "SSD": [("sorghum", 0.55), ("maize", 0.20)],
    "SOM": [("sorghum", 0.55), ("maize", 0.25)],
    "MLI": [("sorghum", 0.30), ("rice", 0.20), ("maize", 0.20)],
    "BFA": [("sorghum", 0.45), ("maize", 0.25)],
    "NER": [("sorghum", 0.55), ("maize", 0.20)],
    "TCD": [("sorghum", 0.55), ("maize", 0.20)],
    "MDG": [("rice", 0.55), ("cassava", 0.25)],
    "MOZ": [("maize", 0.30), ("cassava", 0.35)],
    "ZWE": [("maize", 0.55), ("sorghum", 0.15)],
    "ZAF": [("maize", 0.55), ("wheat", 0.20), ("sorghum", 0.10)],
    "ZMB": [("maize", 0.65), ("cassava", 0.15)],
    "MWI": [("maize", 0.60), ("cassava", 0.15)],
    "RWA": [("maize", 0.30), ("cassava", 0.25)],
    "BDI": [("maize", 0.30), ("cassava", 0.30)],
    "YEM": [("sorghum", 0.45), ("wheat", 0.15)],
    "AFG": [("wheat", 0.70), ("maize", 0.10)],
    "SYR": [("wheat", 0.55), ("maize", 0.10)],
    "IRQ": [("wheat", 0.55), ("rice", 0.15)],
}


def _hemisphere_for(centroid_lat: float | None) -> str:
    if centroid_lat is None:
        return "N"
    if abs(centroid_lat) < 15:
        return "T"
    return "N" if centroid_lat >= 0 else "S"


def main() -> None:
    with cursor() as cur:
        cur.execute(
            "SELECT id, iso3, ST_Y(centroid) AS lat FROM regions WHERE admin_level = 0",
        )
        regions = {r["iso3"]: (r["id"], r["lat"]) for r in cur.fetchall()}

        rc_rows = 0
        cc_rows = 0
        for iso3, crops in REGION_CROPS.items():
            if iso3 not in regions:
                continue
            region_id, lat = regions[iso3]
            hemisphere = _hemisphere_for(lat)
            for crop, share in crops:
                cur.execute(
                    """
                    INSERT INTO region_crops (region_id, crop, share)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (region_id, crop) DO UPDATE SET share = EXCLUDED.share
                    """,
                    (region_id, crop, share),
                )
                rc_rows += 1
                cal = CROP_CALENDAR.get(crop, {}).get(hemisphere) or CROP_CALENDAR[crop].get("T")
                if not cal:
                    cal = next(iter(CROP_CALENDAR[crop].values()))
                cur.execute(
                    """
                    INSERT INTO crop_calendar
                        (region_id, crop, plant_start, plant_end, harvest_start, harvest_end)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (region_id, crop) DO UPDATE
                    SET plant_start = EXCLUDED.plant_start,
                        plant_end = EXCLUDED.plant_end,
                        harvest_start = EXCLUDED.harvest_start,
                        harvest_end = EXCLUDED.harvest_end
                    """,
                    (region_id, crop, cal["plant_start"], cal["plant_end"],
                     cal["harvest_start"], cal["harvest_end"]),
                )
                cc_rows += 1
    print(f"Inserted/updated {rc_rows} region_crops, {cc_rows} crop_calendar rows.")


if __name__ == "__main__":
    main()

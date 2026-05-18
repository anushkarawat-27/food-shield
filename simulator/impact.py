"""Crop-aware geospatial impact model.

For each region in the scenario:
  yield_delta_pct =
      - 100 * sum over crops of
          share[crop] * season_phase_weight(today, crop_calendar[region,crop])
                      * sum over disruptors of
                          severity[disruptor] * sensitivity[crop][disruptor]
  clamped to [-95, 0].

affected_population is scaled by poverty headcount and impact magnitude so
the optimizer demand reflects the most vulnerable share of the population.

Falls back to a flat heuristic if a region has no crop data — preserves the
v0 demo behaviour when seed_crops.py hasn't been run.
"""
from __future__ import annotations

from datetime import datetime, timezone

from api.db import cursor

# Crop sensitivity to each disruptor (0..1). Calibrated from FAO impact reviews:
# wheat is hit hard by frost, rice tolerates floods more, cassava is drought-resilient.
CROP_SENSITIVITY: dict[str, dict[str, float]] = {
    "wheat":   {"drought": 0.70, "flood": 0.45, "heat": 0.55, "pest": 0.40, "frost": 0.85},
    "maize":   {"drought": 0.75, "flood": 0.50, "heat": 0.65, "pest": 0.55, "frost": 0.60},
    "rice":    {"drought": 0.55, "flood": 0.20, "heat": 0.50, "pest": 0.50, "frost": 0.30},
    "sorghum": {"drought": 0.35, "flood": 0.55, "heat": 0.30, "pest": 0.45, "frost": 0.55},
    "cassava": {"drought": 0.25, "flood": 0.60, "heat": 0.30, "pest": 0.40, "frost": 0.70},
}

# Fallback weights when a region has no crop portfolio in the DB.
FALLBACK_DISRUPTOR_WEIGHTS = {
    "drought": 0.45, "flood": 0.30, "heat": 0.25, "pest": 0.20, "frost": 0.35,
}


def _day_of_year(dt: datetime | None = None) -> int:
    return (dt or datetime.now(timezone.utc)).timetuple().tm_yday


def _in_window(doy: int, start: int, end: int) -> bool:
    """Inclusive window on day-of-year, handling wrap-around (e.g. Nov–Feb)."""
    if start <= end:
        return start <= doy <= end
    return doy >= start or doy <= end


def _season_phase_weight(doy: int, plant_s: int, plant_e: int, harv_s: int, harv_e: int) -> float:
    """0 outside growing season; tapered weight in early planting / late harvest;
    full weight (1.0) while crop is actively growing between planting end and harvest start."""
    if _in_window(doy, plant_s, plant_e):
        return 0.6                              # planting — moderate risk
    if _in_window(doy, harv_s, harv_e):
        return 0.5                              # harvest — moderate risk
    # Growing window = between plant_end and harvest_start
    grow_s = plant_e
    grow_e = harv_s
    if _in_window(doy, grow_s, grow_e):
        return 1.0                              # vegetative/reproductive — highest risk
    return 0.0                                  # off-season


def simulate_scenario(scenario: dict[int, dict[str, float]]) -> list[dict]:
    results: list[dict] = []
    if not scenario:
        return results

    region_ids = [int(rid) for rid in scenario.keys()]
    doy = _day_of_year()

    with cursor() as cur:
        cur.execute(
            """
            SELECT id, COALESCE(population, 0) AS population,
                   COALESCE(poverty_pct, 30.0) AS poverty_pct
            FROM regions WHERE id = ANY(%s)
            """,
            (region_ids,),
        )
        region_meta = {r["id"]: r for r in cur.fetchall()}

        cur.execute(
            """
            SELECT rc.region_id, rc.crop, rc.share,
                   cc.plant_start, cc.plant_end, cc.harvest_start, cc.harvest_end
            FROM region_crops rc
            LEFT JOIN crop_calendar cc
              ON cc.region_id = rc.region_id AND cc.crop = rc.crop
            WHERE rc.region_id = ANY(%s)
            """,
            (region_ids,),
        )
        crops_by_region: dict[int, list[dict]] = {}
        for r in cur.fetchall():
            crops_by_region.setdefault(r["region_id"], []).append(r)

    for rid, inputs in scenario.items():
        rid = int(rid)
        crops = crops_by_region.get(rid, [])
        meta = region_meta.get(rid, {"population": 0, "poverty_pct": 30.0})

        if crops:
            delta_sum = 0.0
            for c in crops:
                sens = CROP_SENSITIVITY.get(c["crop"], {})
                if c["plant_start"] is None:
                    phase = 0.4                                # unknown calendar — partial
                else:
                    phase = _season_phase_weight(
                        doy, c["plant_start"], c["plant_end"],
                        c["harvest_start"], c["harvest_end"],
                    )
                if phase == 0:
                    continue
                disrupt_total = sum(
                    sens.get(k, 0.0) * float(v) for k, v in inputs.items()
                )
                delta_sum += c["share"] * phase * disrupt_total
            yield_delta_pct = max(-95.0, -100.0 * delta_sum)
            impact_magnitude = min(1.0, delta_sum)
        else:
            # Fallback: flat weighted heuristic
            weighted = sum(
                FALLBACK_DISRUPTOR_WEIGHTS.get(k, 0) * float(v) for k, v in inputs.items()
            )
            yield_delta_pct = max(-90.0, -100.0 * weighted)
            impact_magnitude = min(1.0, weighted)

        # Affected population = population × poverty pct × impact magnitude.
        # Demand for aid scales with the most vulnerable affected share.
        pop = meta["population"] or 0
        poverty = (meta["poverty_pct"] or 30.0) / 100.0
        affected = int(pop * poverty * impact_magnitude)

        results.append(
            {
                "region_id": rid,
                "yield_delta_pct": round(yield_delta_pct, 2),
                "affected_population": affected,
            }
        )
    return results


# Compatibility export for projector.py
DISRUPTOR_WEIGHTS = FALLBACK_DISRUPTOR_WEIGHTS

"""Food aid allocation MILP — Weeks 7-8.

Decision variables:  x[d, r] = tonnes shipped from depot d to region r
Constraints:
  sum_r x[d, r]            <= depot[d].stock_tonnes        (depot capacity)
  sum_d x[d, r]            <= demand[r]                    (no over-allocation)
  sum_{d, r} x[d, r]       <= total_tonnage                (global tonnage cap)
  sum_{d, r} cost[d, r]·x  <= total_budget_usd             (global budget cap)
Objective:
  maximize sum_{d, r} priority_weight[r] · x[d, r]

priority_weight[r] = 1 + α·(poverty_pct[r] / 100)            base vulnerability
                       + β·(impact_magnitude[r])             current shock severity
                       + γ·1[r ∈ priority_population_groups] caller-supplied bias
Conflict regions are dropped from `demand` when avoid_conflict_zones=True so the
LP never ships into unsafe areas.
"""
from __future__ import annotations

import pulp

from api.db import cursor
from simulator.impact import simulate_scenario

# Tunable weights on the vulnerability-weighted objective.
ALPHA_POVERTY = 2.0
BETA_IMPACT = 1.5
GAMMA_PRIORITY = 1.0

DEFAULT_COST_PER_TONNE_USD = 200.0
DEMAND_PEOPLE_PER_TONNE = 1000.0   # ~1 t feeds ~1000 people for a short emergency window


def _fetch_region_meta(region_ids: list[int]) -> dict[int, dict]:
    """Pull poverty + ISO + name for the regions in the scenario. Best-effort:
    if the DB is unreachable, return defaults so the LP still solves."""
    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT id, name, iso3, COALESCE(poverty_pct, 30.0) AS poverty_pct
                FROM regions WHERE id = ANY(%s)
                """,
                (region_ids,),
            )
            return {r["id"]: dict(r) for r in cur.fetchall()}
    except Exception:
        return {rid: {"id": rid, "name": f"region_{rid}", "iso3": "", "poverty_pct": 30.0}
                for rid in region_ids}


def _fetch_depots(total_tonnage: float) -> list[dict]:
    """Pull depots; synthesize a virtual depot if the table is empty / unreachable."""
    try:
        with cursor() as cur:
            cur.execute("SELECT id, name, stock_tonnes FROM depots ORDER BY id")
            depots = [dict(r) for r in cur.fetchall()]
    except Exception:
        depots = []
    if not depots:
        depots = [{"id": 0, "name": "virtual_depot", "stock_tonnes": total_tonnage}]
    return depots


def _conflict_region_ids(region_ids: list[int]) -> set[int]:
    """Region IDs that intersect any active conflict zone."""
    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT r.id
                FROM regions r
                JOIN conflict_zones c ON ST_Intersects(r.geom, c.geom)
                WHERE r.id = ANY(%s)
                """,
                (region_ids,),
            )
            return {row["id"] for row in cur.fetchall()}
    except Exception:
        return set()


def _priority_weight(
    rid: int,
    meta: dict,
    impact_mag: float,
    priority_groups: list[str],
) -> float:
    """Higher is better — gets more aid in the LP solution."""
    poverty = float(meta.get("poverty_pct", 30.0)) / 100.0
    iso3 = (meta.get("iso3") or "").upper()
    in_priority = any(
        g.upper() == iso3 or g.lower() == (meta.get("name") or "").lower()
        for g in priority_groups
    )
    return (
        1.0
        + ALPHA_POVERTY * poverty
        + BETA_IMPACT * float(impact_mag)
        + (GAMMA_PRIORITY if in_priority else 0.0)
    )


def recommend_allocation(
    scenario: dict[int, dict[str, float]],
    total_tonnage: float,
    total_budget_usd: float,
    priority_groups: list[str],
    avoid_conflict_zones: bool,
) -> dict:
    impacts = simulate_scenario(scenario)
    if not impacts:
        return {"allocations": [], "unmet_demand_tonnes": 0.0, "total_cost_usd": 0.0,
                "skipped_conflict_regions": [], "objective_value": 0.0}

    region_ids = [i["region_id"] for i in impacts]
    region_meta = _fetch_region_meta(region_ids)

    # Demand in tonnes: scaled by affected vulnerable population.
    demand_all = {
        i["region_id"]: max(0.0, i["affected_population"] / DEMAND_PEOPLE_PER_TONNE)
        for i in impacts
    }
    impact_by_region = {
        i["region_id"]: min(1.0, abs(i["yield_delta_pct"]) / 100.0) for i in impacts
    }

    skipped_conflict: list[int] = []
    if avoid_conflict_zones:
        conflict = _conflict_region_ids(region_ids)
        skipped_conflict = sorted(rid for rid in conflict if rid in demand_all)
        for rid in skipped_conflict:
            demand_all.pop(rid, None)

    # Drop zero-demand regions — they contribute nothing and bloat the LP
    demand = {rid: q for rid, q in demand_all.items() if q > 0.0}
    if not demand:
        return {"allocations": [], "unmet_demand_tonnes": 0.0, "total_cost_usd": 0.0,
                "skipped_conflict_regions": skipped_conflict, "objective_value": 0.0}

    depots = _fetch_depots(total_tonnage)
    cost_per_tonne = DEFAULT_COST_PER_TONNE_USD

    weight = {
        rid: _priority_weight(rid, region_meta.get(rid, {}), impact_by_region[rid], priority_groups)
        for rid in demand
    }

    prob = pulp.LpProblem("food_aid", pulp.LpMaximize)
    x = {
        (d["id"], rid): pulp.LpVariable(f"x_{d['id']}_{rid}", lowBound=0)
        for d in depots
        for rid in demand
    }

    # Vulnerability-weighted objective
    prob += pulp.lpSum(weight[rid] * x[d["id"], rid] for d in depots for rid in demand)

    # Capacity / demand / global caps
    for d in depots:
        prob += pulp.lpSum(x[d["id"], rid] for rid in demand) <= float(d["stock_tonnes"] or 0.0)
    for rid, q in demand.items():
        prob += pulp.lpSum(x[d["id"], rid] for d in depots) <= q
    prob += pulp.lpSum(x.values()) <= total_tonnage
    prob += pulp.lpSum(cost_per_tonne * v for v in x.values()) <= total_budget_usd

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    allocations = []
    total_cost = 0.0
    for (depot_id, rid), var in x.items():
        tonnes = var.value() or 0.0
        if tonnes <= 0.01:
            continue
        cost = tonnes * cost_per_tonne
        total_cost += cost
        depot_name = next(d["name"] for d in depots if d["id"] == depot_id)
        coverage = (tonnes / demand[rid] * 100.0) if demand[rid] > 0 else 0.0
        allocations.append(
            {
                "region_id": rid,
                "tonnes": round(tonnes, 2),
                "from_depot": depot_name,
                "cost_usd": round(cost, 2),
                "coverage_pct": round(coverage, 1),
                "priority_weight": round(weight[rid], 3),
            }
        )

    delivered = sum(a["tonnes"] for a in allocations)
    unmet = max(0.0, sum(demand.values()) - delivered)

    return {
        "allocations": allocations,
        "unmet_demand_tonnes": round(unmet, 2),
        "total_cost_usd": round(total_cost, 2),
        "skipped_conflict_regions": skipped_conflict,
        "objective_value": round(pulp.value(prob.objective) or 0.0, 3),
    }

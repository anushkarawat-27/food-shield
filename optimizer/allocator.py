"""Food aid allocation MILP — Weeks 7-8.

Decision variables:  x[d, r] = tonnes shipped from depot d to region r
Constraints:
  sum_r x[d,r] <= depot[d].stock_tonnes
  sum_d x[d,r] <= demand[r]
  sum_{d,r} x[d,r] <= total_tonnage
  sum_{d,r} cost[d,r] * x[d,r] <= total_budget_usd
Objective:
  maximize sum_{d,r} priority_weight[r] * x[d,r]

v0 below is a greedy fallback (no PuLP solve) so the endpoint returns shape-correct
data before the LP is wired up. Replace with PuLP/OR-Tools in Week 7.
"""
from __future__ import annotations

import pulp

from api.db import cursor
from simulator.impact import simulate_scenario


def recommend_allocation(
    scenario: dict[int, dict[str, float]],
    total_tonnage: float,
    total_budget_usd: float,
    priority_groups: list[str],
    avoid_conflict_zones: bool,
) -> dict:
    impacts = simulate_scenario(scenario)
    # Demand: 1 tonne per 1000 affected people (placeholder ratio).
    demand = {i["region_id"]: max(0.0, i["affected_population"] / 1000.0) for i in impacts}

    with cursor() as cur:
        cur.execute("SELECT id, name, stock_tonnes FROM depots ORDER BY id")
        depots = list(cur.fetchall())

    if not depots:
        # Synthesize a single virtual depot for v0 so the endpoint returns useful data.
        depots = [{"id": 0, "name": "virtual_depot", "stock_tonnes": total_tonnage}]

    # Cost matrix placeholder: flat $200/tonne. Replace with routes table lookup.
    cost_per_tonne = 200.0

    prob = pulp.LpProblem("food_aid", pulp.LpMaximize)
    x = {
        (d["id"], rid): pulp.LpVariable(f"x_{d['id']}_{rid}", lowBound=0)
        for d in depots
        for rid in demand
    }

    prob += pulp.lpSum(x.values())  # maximize total delivered tonnage

    for d in depots:
        prob += pulp.lpSum(x[d["id"], rid] for rid in demand) <= d["stock_tonnes"]
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
            }
        )

    delivered = sum(a["tonnes"] for a in allocations)
    unmet = max(0.0, sum(demand.values()) - delivered)

    return {
        "allocations": allocations,
        "unmet_demand_tonnes": round(unmet, 2),
        "total_cost_usd": round(total_cost, 2),
    }

"""Policy / scenario export — emits a recommended-allocation CSV for download.

POST /export/policy   body = same shape as /recommend
Response: text/csv
  region_id, region_name, iso3, from_depot, tonnes, cost_usd, coverage_pct, priority_weight
Trailing rows: TOTAL, UNMET_DEMAND, SKIPPED_CONFLICT_REGIONS.

The endpoint is POST (not GET) because allocation results aren't cached server-side
yet — clients re-submit the scenario and we hand back the CSV in one round trip.
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.db import cursor
from optimizer.allocator import recommend_allocation

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    scenario: dict[int, dict[str, float]]
    total_tonnage: float = Field(..., gt=0)
    total_budget_usd: float = Field(..., gt=0)
    priority_population_groups: list[str] = []
    avoid_conflict_zones: bool = True
    filename: str = "foodshield_policy.csv"


def _region_lookup(region_ids: list[int]) -> dict[int, dict]:
    if not region_ids:
        return {}
    try:
        with cursor() as cur:
            cur.execute(
                "SELECT id, name, iso3 FROM regions WHERE id = ANY(%s)",
                (region_ids,),
            )
            return {r["id"]: dict(r) for r in cur.fetchall()}
    except Exception:
        return {}


@router.post("/policy")
def export_policy(req: ExportRequest):
    result = recommend_allocation(
        scenario=req.scenario,
        total_tonnage=req.total_tonnage,
        total_budget_usd=req.total_budget_usd,
        priority_groups=req.priority_population_groups,
        avoid_conflict_zones=req.avoid_conflict_zones,
    )
    region_ids = [a["region_id"] for a in result["allocations"]] + result.get(
        "skipped_conflict_regions", []
    )
    regions = _region_lookup(region_ids)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "region_id", "region_name", "iso3", "from_depot",
            "tonnes", "cost_usd", "coverage_pct", "priority_weight",
        ]
    )

    total_t = 0.0
    total_cost = 0.0
    for a in result["allocations"]:
        meta = regions.get(a["region_id"], {})
        writer.writerow(
            [
                a["region_id"],
                meta.get("name", ""),
                meta.get("iso3", ""),
                a["from_depot"],
                a["tonnes"],
                a["cost_usd"],
                a["coverage_pct"],
                a.get("priority_weight", ""),
            ]
        )
        total_t += a["tonnes"]
        total_cost += a["cost_usd"]

    writer.writerow([])
    writer.writerow(["TOTAL_TONNES", "", "", "", round(total_t, 2), round(total_cost, 2), "", ""])
    writer.writerow(["UNMET_DEMAND_TONNES", "", "", "", result["unmet_demand_tonnes"], "", "", ""])
    skipped = result.get("skipped_conflict_regions", [])
    if skipped:
        writer.writerow(
            ["SKIPPED_CONFLICT_REGIONS", "", "", "",
             ";".join(str(s) for s in skipped), "", "", ""]
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{req.filename}"'},
    )

from fastapi import APIRouter
from pydantic import BaseModel, Field

from optimizer.allocator import recommend_allocation

router = APIRouter(prefix="/recommend", tags=["recommend"])


class RecommendRequest(BaseModel):
    scenario: dict[int, dict[str, float]]
    total_tonnage: float = Field(..., gt=0)
    total_budget_usd: float = Field(..., gt=0)
    priority_population_groups: list[str] = []
    avoid_conflict_zones: bool = True


class Allocation(BaseModel):
    region_id: int
    tonnes: float
    from_depot: str
    cost_usd: float
    coverage_pct: float
    priority_weight: float | None = None


class RecommendResponse(BaseModel):
    allocations: list[Allocation]
    unmet_demand_tonnes: float
    total_cost_usd: float
    skipped_conflict_regions: list[int] = []
    objective_value: float | None = None


@router.post("", response_model=RecommendResponse)
def recommend(req: RecommendRequest) -> RecommendResponse:
    result = recommend_allocation(
        scenario=req.scenario,
        total_tonnage=req.total_tonnage,
        total_budget_usd=req.total_budget_usd,
        priority_groups=req.priority_population_groups,
        avoid_conflict_zones=req.avoid_conflict_zones,
    )
    return RecommendResponse(
        allocations=[Allocation(**a) for a in result["allocations"]],
        unmet_demand_tonnes=result["unmet_demand_tonnes"],
        total_cost_usd=result["total_cost_usd"],
        skipped_conflict_regions=result.get("skipped_conflict_regions", []),
        objective_value=result.get("objective_value"),
    )

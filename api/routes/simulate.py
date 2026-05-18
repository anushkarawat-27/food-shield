from fastapi import APIRouter
from pydantic import BaseModel, Field

from simulator.impact import simulate_scenario

router = APIRouter(prefix="/simulate", tags=["simulate"])


class RegionInputs(BaseModel):
    drought: float = Field(0.0, ge=0.0, le=1.0)
    flood: float = Field(0.0, ge=0.0, le=1.0)
    heat: float = Field(0.0, ge=0.0, le=1.0)
    pest: float = Field(0.0, ge=0.0, le=1.0)
    frost: float = Field(0.0, ge=0.0, le=1.0)


class SimulateRequest(BaseModel):
    scenario: dict[int, RegionInputs]


class RegionImpact(BaseModel):
    region_id: int
    yield_delta_pct: float
    affected_population: int


@router.post("", response_model=list[RegionImpact])
def simulate(req: SimulateRequest) -> list[RegionImpact]:
    payload = {rid: inputs.model_dump() for rid, inputs in req.scenario.items()}
    return [RegionImpact(**r) for r in simulate_scenario(payload)]

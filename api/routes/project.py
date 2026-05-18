from fastapi import APIRouter
from pydantic import BaseModel

from simulator.projector import project_scenario

router = APIRouter(prefix="/project", tags=["project"])


class ProjectRequest(BaseModel):
    scenario: dict[int, dict[str, float]]
    horizons_months: list[int] = [3, 6, 12]


class Projection(BaseModel):
    region_id: int
    horizon_months: int
    ipc_phase: float
    ci_low: float
    ci_high: float


@router.post("", response_model=list[Projection])
def project(req: ProjectRequest) -> list[Projection]:
    return [Projection(**p) for p in project_scenario(req.scenario, req.horizons_months)]

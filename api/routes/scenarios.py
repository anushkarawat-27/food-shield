from fastapi import APIRouter, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from api.db import cursor

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class ScenarioPayload(BaseModel):
    name: str
    payload: dict


@router.post("")
def create_scenario(s: ScenarioPayload) -> dict:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO scenarios (name, payload) VALUES (%s, %s) RETURNING id",
            (s.name, Jsonb(s.payload)),
        )
        row = cur.fetchone()
    return {"id": row["id"]}


@router.get("/{scenario_id}")
def get_scenario(scenario_id: int) -> dict:
    with cursor() as cur:
        cur.execute("SELECT id, name, payload, created_at FROM scenarios WHERE id = %s", (scenario_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "scenario not found")
    return row


@router.get("")
def list_scenarios() -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT id, name, created_at FROM scenarios ORDER BY created_at DESC LIMIT 50")
        return list(cur.fetchall())

"""Continuous alert agent. Watches disruptor_events stream + projections;
pushes alerts to Redis pubsub when a region crosses a risk threshold.

Trigger rule (v0): any region whose 6-month projected IPC phase >= 3.0
publishes an alert with the contributing disruptors.
"""
from __future__ import annotations

import json
import os
import time

import redis

from api.db import cursor

ALERT_CHANNEL = "foodshield:alerts"
POLL_SECONDS = 60
IPC_ALERT_THRESHOLD = 3.0


def run() -> None:
    r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    seen: set[int] = set()
    while True:
        with cursor() as cur:
            cur.execute(
                """
                SELECT region_id, ipc_phase, generated_at
                FROM projections
                WHERE horizon_months = 6
                  AND ipc_phase >= %s
                  AND generated_at > NOW() - INTERVAL '1 day'
                """,
                (IPC_ALERT_THRESHOLD,),
            )
            for row in cur.fetchall():
                if row["region_id"] in seen:
                    continue
                seen.add(row["region_id"])
                r.publish(ALERT_CHANNEL, json.dumps({
                    "region_id": row["region_id"],
                    "ipc_phase": row["ipc_phase"],
                    "ts": row["generated_at"].isoformat(),
                }))
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()

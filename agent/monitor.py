"""Continuous food-insecurity alert agent.

Polls `disruptor_events` for each region, aggregates per-region recent
severity into a single weighted score, and raises an alert when the score
crosses a threshold. Alerts are deduped per region (we don't re-fire while
the region is still over the threshold) and written to the `alerts` table.

This is wrapped as a Prefect flow so it can run as a scheduled job in
production. For local dev / CI it also exposes `run_once()` which performs
one polling pass with no scheduling, so it's testable as a plain function.

Optional Redis pubsub: if REDIS_URL is set, every new alert is also broadcast
on `foodshield:alerts` so the dashboard can subscribe.

Trigger rule:
    score(r) = Σ_d weight[d] · max_recent_severity[d]
    alert if score(r) >= ALERT_SCORE_THRESHOLD
    or the 6-month projected IPC phase >= IPC_ALERT_THRESHOLD.
"""
from __future__ import annotations

import json
import os
from typing import Any

from api.db import cursor
from simulator.impact import FALLBACK_DISRUPTOR_WEIGHTS
from simulator.projector import project_scenario

ALERT_SCORE_THRESHOLD = 0.45    # tripped when weighted severity exceeds this
IPC_ALERT_THRESHOLD = 3.0       # alternatively, projected 6-month IPC ≥ this
LOOKBACK_DAYS = 14              # events older than this don't count


def _publish_redis(payload: dict[str, Any]) -> None:
    """Best-effort pubsub. Silently no-ops if redis isn't configured."""
    url = os.environ.get("REDIS_URL")
    if not url:
        return
    try:
        import redis
        r = redis.from_url(url)
        r.publish("foodshield:alerts", json.dumps(payload, default=str))
    except Exception as e:                                # noqa: BLE001
        print(f"[agent] redis publish failed: {e}", flush=True)


def _per_region_severity() -> dict[int, dict[str, float]]:
    """{region_id: {disruptor: max-severity-in-last-LOOKBACK_DAYS}}."""
    with cursor() as cur:
        cur.execute(
            """
            SELECT r.id AS region_id, e.disruptor_type, MAX(e.severity) AS sev
            FROM regions r
            JOIN disruptor_events e ON ST_Intersects(r.geom, e.geom)
            WHERE e.started_at >= NOW() - INTERVAL %s
            GROUP BY r.id, e.disruptor_type
            """,
            (f"{LOOKBACK_DAYS} days",),
        )
        out: dict[int, dict[str, float]] = {}
        for row in cur.fetchall():
            out.setdefault(row["region_id"], {})[row["disruptor_type"]] = float(row["sev"])
        return out


def _open_alert_region_ids() -> set[int]:
    """Regions that already have an unresolved alert — skip to avoid spam."""
    with cursor() as cur:
        cur.execute("SELECT region_id FROM alerts WHERE resolved_at IS NULL")
        return {row["region_id"] for row in cur.fetchall()}


def _weighted_score(severities: dict[str, float]) -> float:
    return sum(FALLBACK_DISRUPTOR_WEIGHTS.get(d, 0.0) * s for d, s in severities.items())


def _insert_alert(
    region_id: int,
    score: float,
    threshold: float,
    severities: dict[str, float],
    ipc_6mo: float | None,
) -> None:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts (region_id, severity_score, threshold, top_disruptors, ipc_phase_6mo)
            VALUES (%s, %s, %s, %s::jsonb, %s)
            ON CONFLICT DO NOTHING
            """,
            (region_id, round(score, 3), threshold, json.dumps(severities), ipc_6mo),
        )


def run_once() -> dict[str, Any]:
    """One polling pass. Returns a summary dict for logging/testing."""
    severities_by_region = _per_region_severity()
    if not severities_by_region:
        return {"polled": 0, "fired": 0, "skipped_open": 0}

    open_alerts = _open_alert_region_ids()

    # One projection call covers everything we care about right now.
    projections = project_scenario(severities_by_region, horizons=[6])
    proj_by_region = {p["region_id"]: p["ipc_phase"] for p in projections}

    fired = 0
    skipped_open = 0
    for rid, sevs in severities_by_region.items():
        if rid in open_alerts:
            skipped_open += 1
            continue
        score = _weighted_score(sevs)
        ipc6 = proj_by_region.get(rid)
        score_trip = score >= ALERT_SCORE_THRESHOLD
        ipc_trip = ipc6 is not None and ipc6 >= IPC_ALERT_THRESHOLD
        if not (score_trip or ipc_trip):
            continue
        _insert_alert(
            rid,
            score=score,
            threshold=ALERT_SCORE_THRESHOLD if score_trip else IPC_ALERT_THRESHOLD,
            severities=sevs,
            ipc_6mo=ipc6,
        )
        _publish_redis(
            {
                "region_id": rid,
                "severity_score": round(score, 3),
                "ipc_phase_6mo": ipc6,
                "top_disruptors": sevs,
                "trigger": "score" if score_trip else "ipc",
            }
        )
        fired += 1

    return {
        "polled": len(severities_by_region),
        "fired": fired,
        "skipped_open": skipped_open,
        "open_alerts_before": len(open_alerts),
    }


# ---------------------------------------------------------------------------
# Prefect wrapper — lets this be deployed on a schedule.
# Importing Prefect is heavy, so we hide it behind a `flow()` function.
# ---------------------------------------------------------------------------
def flow():                                                # pragma: no cover
    from prefect import flow as _flow, get_run_logger

    @_flow(name="foodshield-monitor")
    def _run():
        logger = get_run_logger()
        result = run_once()
        logger.info(f"monitor pass: {result}")
        return result

    return _run


if __name__ == "__main__":                                 # pragma: no cover
    # Prefer Prefect when installed (gives logs + retries + scheduling hooks).
    try:
        flow()()
    except ImportError:
        print(run_once())

"""Projection model — Weeks 5-6.

v0 heuristic: IPC phase scales linearly with weighted disruptor severity,
horizon adds uncertainty. Replace with trained XGBoost regressors per horizon.

Training data plan (Week 5):
- Features: rolling-window disruptor severity per region, poverty_pct, baseline yield trend
- Target: FEWS NET IPC phase per region 3/6/12 months ahead
- One model per horizon, quantile regression for CI bands.
"""
from __future__ import annotations

from simulator.impact import DISRUPTOR_WEIGHTS


def project_scenario(
    scenario: dict[int, dict[str, float]],
    horizons: list[int],
) -> list[dict]:
    out: list[dict] = []
    for rid, inputs in scenario.items():
        weighted = sum(DISRUPTOR_WEIGHTS.get(k, 0) * float(v) for k, v in inputs.items())
        base_phase = 1.0 + 4.0 * min(1.0, weighted)  # IPC 1..5
        for h in horizons:
            # Phase drifts up with horizon, CI widens
            phase = min(5.0, base_phase + 0.05 * h)
            ci = 0.3 + 0.05 * h
            out.append(
                {
                    "region_id": int(rid),
                    "horizon_months": h,
                    "ipc_phase": round(phase, 2),
                    "ci_low": round(max(1.0, phase - ci), 2),
                    "ci_high": round(min(5.0, phase + ci), 2),
                }
            )
    return out

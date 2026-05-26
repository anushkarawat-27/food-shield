"""Projection model — Weeks 5-6.

Loads trained XGBoost quantile regressors from models/projector_h{H}_q{Q}.joblib
and returns IPC-phase point estimates (p50) with CI bands (p10, p90).

Falls back to a deterministic heuristic if models aren't on disk, so the API
keeps working on fresh clones / CI runs.

Train the models with:  python -m simulator.train_projector
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

from simulator.impact import DISRUPTOR_WEIGHTS

HORIZONS_DEFAULT = [3, 6, 12]
QUANTILES = [10, 50, 90]
DISRUPTORS = ["drought", "flood", "heat", "pest", "frost"]
WINDOWS_DAYS = [30, 90, 180]

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
META_PATH = MODELS_DIR / "projector_meta.json"


def _load_models() -> dict | None:
    """Return {(h, q): model, '_meta': dict} or None if any artifact is missing."""
    if not META_PATH.exists():
        return None
    try:
        import joblib  # heavy import deferred
    except ImportError:
        return None

    meta = json.loads(META_PATH.read_text())
    bundle: dict = {"_meta": meta}
    for h in meta["horizons"]:
        for q in [int(x * 100) for x in meta["quantiles"]]:
            p = MODELS_DIR / f"projector_h{h}_q{q:02d}.joblib"
            if not p.exists():
                return None
            bundle[(h, q)] = joblib.load(p)
    return bundle


_MODELS: dict | None = _load_models()


def _features_for_region(inputs: dict[str, float], poverty_pct: float = 30.0) -> np.ndarray:
    """Build the feature vector the projector was trained on.

    The trainer uses three windowed severities per disruptor (30/90/180d). At
    inference time the user passes a single severity per disruptor (the
    'current' state of the scenario), so we replicate it across the three
    windows. This is the conventional bridge between point-in-time scenarios
    and rolling-window training data.
    """
    doy = datetime.now(timezone.utc).timetuple().tm_yday
    feats: list[float] = []
    for d in DISRUPTORS:
        sev = float(inputs.get(d, 0.0))
        for _ in WINDOWS_DAYS:
            feats.append(sev)
    feats.append(float(poverty_pct))
    feats.append(0.0)  # yield_trend — unknown at scenario time
    feats.append(math.cos(2 * math.pi * doy / 365.25))
    feats.append(math.sin(2 * math.pi * doy / 365.25))
    return np.array(feats, dtype=np.float32).reshape(1, -1)


def _heuristic(rid: int, inputs: dict[str, float], horizons: Iterable[int]) -> list[dict]:
    weighted = sum(DISRUPTOR_WEIGHTS.get(k, 0) * float(v) for k, v in inputs.items())
    base_phase = 1.0 + 4.0 * min(1.0, weighted)
    out: list[dict] = []
    for h in horizons:
        phase = min(5.0, base_phase + 0.05 * h)
        ci = 0.3 + 0.05 * h
        out.append(
            {
                "region_id": int(rid),
                "horizon_months": int(h),
                "ipc_phase": round(phase, 2),
                "ci_low": round(max(1.0, phase - ci), 2),
                "ci_high": round(min(5.0, phase + ci), 2),
                "source": "heuristic",
            }
        )
    return out


def _poverty_lookup(region_ids: list[int]) -> dict[int, float]:
    """Best-effort poverty lookup. Silent default if DB unreachable."""
    try:
        from api.db import cursor

        with cursor() as cur:
            cur.execute(
                "SELECT id, COALESCE(poverty_pct, 30.0) AS poverty_pct "
                "FROM regions WHERE id = ANY(%s)",
                (region_ids,),
            )
            return {r["id"]: float(r["poverty_pct"]) for r in cur.fetchall()}
    except Exception:
        return {}


def project_scenario(
    scenario: dict[int, dict[str, float]],
    horizons: list[int] | None = None,
) -> list[dict]:
    horizons = horizons or HORIZONS_DEFAULT
    if not scenario:
        return []

    region_ids = [int(r) for r in scenario]
    poverty = _poverty_lookup(region_ids)

    if _MODELS is None:
        out: list[dict] = []
        for rid, inputs in scenario.items():
            out.extend(_heuristic(rid, inputs, horizons))
        return out

    out = []
    for rid, inputs in scenario.items():
        X = _features_for_region(inputs, poverty_pct=poverty.get(int(rid), 30.0))
        for h in horizons:
            p10 = float(_MODELS[(h, 10)].predict(X)[0])
            p50 = float(_MODELS[(h, 50)].predict(X)[0])
            p90 = float(_MODELS[(h, 90)].predict(X)[0])
            # Enforce monotone quantile ordering + IPC range
            lo, mid, hi = sorted([p10, p50, p90])
            out.append(
                {
                    "region_id": int(rid),
                    "horizon_months": int(h),
                    "ipc_phase": round(max(1.0, min(5.0, mid)), 2),
                    "ci_low": round(max(1.0, min(5.0, lo)), 2),
                    "ci_high": round(max(1.0, min(5.0, hi)), 2),
                    "source": _MODELS["_meta"]["source"],
                }
            )
    return out

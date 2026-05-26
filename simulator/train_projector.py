"""Train per-horizon quantile-regression projectors for IPC phase (1..5).

Outputs:  models/projector_h{3,6,12}_q{10,50,90}.joblib
          models/projector_meta.json  (feature schema + train metrics)

Two data modes:
  1. DB mode — pulls rolling disruptor severity per region from disruptor_events,
     joined with regions.poverty_pct, and IPC labels from a future
     ipc_observations table (populated by fewsnet ingestion).
  2. Synthetic mode — used when DB has no events / no labels. Generates a
     calibrated corpus from the same impact-model physics the simulator uses,
     so the trained models capture meaningful structure even before live
     FEWS NET labels are wired in. This is flagged in models/projector_meta.json
     so downstream code knows it's pre-production.

Run:  python -m simulator.train_projector
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
HORIZONS = [3, 6, 12]
QUANTILES = [0.10, 0.50, 0.90]
DISRUPTORS = ["drought", "flood", "heat", "pest", "frost"]
WINDOWS_DAYS = [30, 90, 180]

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

FEATURE_COLS: list[str] = (
    [f"sev_{d}_{w}d" for d in DISRUPTORS for w in WINDOWS_DAYS]
    + ["poverty_pct", "yield_trend", "season_cos", "season_sin"]
)


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------
def _try_db_corpus() -> pd.DataFrame | None:
    """Attempt to build the training corpus from DB. Returns None if unusable."""
    if "DATABASE_URL" not in os.environ:
        return None
    try:
        from api.db import cursor  # local import so synthetic mode has no DB dep
    except Exception:
        return None

    try:
        with cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM disruptor_events")
            n_events = cur.fetchone()["n"]
            cur.execute("SELECT to_regclass('public.ipc_observations') IS NOT NULL AS ok")
            has_labels = bool(cur.fetchone()["ok"])
            if not has_labels:
                print("[db] ipc_observations table missing; using synthetic", file=sys.stderr)
                return None
            cur.execute("SELECT COUNT(*) AS n FROM ipc_observations")
            n_labels = cur.fetchone()["n"]
    except Exception as e:
        print(f"[db] unreachable ({e}); falling back to synthetic", file=sys.stderr)
        return None

    # Need both upstream events and labels in non-trivial quantity to learn
    # generalizable patterns; otherwise synthetic gives more reliable models.
    if n_events < 500 or n_labels < 200:
        print(
            f"[db] events={n_events} labels={n_labels} — corpus too small, "
            "using synthetic instead",
            file=sys.stderr,
        )
        return None

    # ------------------------------------------------------------------
    # Build a row per (region, observation, horizon).
    # Features: rolling-window mean severity per disruptor over 30/90/180 days
    # ending at the observation's period_start MINUS the horizon (the moment
    # at which the projector would have to make a forecast).
    # Target: IPC phase observed at period_start.
    # ------------------------------------------------------------------
    rows: list[dict] = []
    with cursor() as cur:
        cur.execute(
            """
            SELECT o.region_id, o.period_start, o.ipc_phase,
                   COALESCE(r.poverty_pct, 30.0) AS poverty_pct
            FROM ipc_observations o
            JOIN regions r ON r.id = o.region_id
            WHERE o.period_kind = 'CS'
            """
        )
        observations = list(cur.fetchall())

        for obs in observations:
            rid = obs["region_id"]
            t0 = obs["period_start"]
            for h in HORIZONS:
                feature_time = t0 - timedelta(days=30 * h)
                feats: dict[str, float] = {}
                # Mean severity per (disruptor, window) ending at feature_time.
                cur.execute(
                    """
                    SELECT disruptor_type,
                           AVG(severity) FILTER (WHERE started_at >= %s - INTERVAL '30 days')  AS w30,
                           AVG(severity) FILTER (WHERE started_at >= %s - INTERVAL '90 days')  AS w90,
                           AVG(severity) FILTER (WHERE started_at >= %s - INTERVAL '180 days') AS w180
                    FROM disruptor_events e
                    JOIN regions r2 ON ST_Intersects(r2.geom, e.geom)
                    WHERE r2.id = %s AND e.started_at <= %s
                    GROUP BY disruptor_type
                    """,
                    (feature_time, feature_time, feature_time, rid, feature_time),
                )
                window_rows = {r["disruptor_type"]: r for r in cur.fetchall()}
                for d in DISRUPTORS:
                    wr = window_rows.get(d, {})
                    for w_name, w_col in (("30d", "w30"), ("90d", "w90"), ("180d", "w180")):
                        feats[f"sev_{d}_{w_name}"] = float(wr.get(w_col) or 0.0)

                doy = t0.timetuple().tm_yday
                feats["poverty_pct"] = float(obs["poverty_pct"])
                feats["yield_trend"] = 0.0  # plug yield_baseline slope here when populated
                feats["season_cos"] = math.cos(2 * math.pi * doy / 365.25)
                feats["season_sin"] = math.sin(2 * math.pi * doy / 365.25)

                rows.append({"region_id": rid, "snapshot_date": t0, "horizon_months": h,
                             "ipc_phase": float(obs["ipc_phase"]), **feats})

    if not rows:
        print("[db] joined corpus came back empty; falling back to synthetic", file=sys.stderr)
        return None
    return pd.DataFrame(rows)


def _synthetic_corpus(
    n_regions: int = 200,
    n_snapshots: int = 60,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a training corpus that matches our impact-model physics.

    For each (region, snapshot) we draw recent disruptor severities, compute
    a 'true' IPC phase using a nonlinear function of severity × poverty ×
    season, then add observation noise. Horizon labels add forward-time drift
    and uncertainty so quantile bands have signal to learn.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict] = []

    for region_id in range(n_regions):
        # Stable region traits
        poverty = float(np.clip(rng.normal(35.0, 18.0), 2.0, 85.0))
        yield_trend = float(np.clip(rng.normal(0.0, 0.04), -0.15, 0.10))
        # Region-specific disruptor exposure baseline (some regions are dry, etc.)
        base_exposure = {d: float(np.clip(rng.beta(1.4, 5.0), 0.0, 0.7)) for d in DISRUPTORS}

        for snap in range(n_snapshots):
            # Random snapshot date over last ~5 years
            days_back = int(rng.integers(0, 365 * 5))
            snap_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            doy = snap_date.timetuple().tm_yday
            season_cos = math.cos(2 * math.pi * doy / 365.25)
            season_sin = math.sin(2 * math.pi * doy / 365.25)

            # Rolling-window severities: longer windows are smoother
            feats: dict[str, float] = {}
            window_severity: dict[str, float] = {}
            for d in DISRUPTORS:
                base = base_exposure[d]
                # Acute spike on top of chronic exposure
                spike = rng.gamma(1.3, 0.18) if rng.random() < 0.20 else 0.0
                trend = float(np.clip(base + spike + rng.normal(0, 0.05), 0.0, 1.0))
                # window means: 30d roughly = trend; 90d/180d trend toward base
                feats[f"sev_{d}_30d"] = float(np.clip(trend + rng.normal(0, 0.04), 0, 1))
                feats[f"sev_{d}_90d"] = float(np.clip(0.6 * trend + 0.4 * base + rng.normal(0, 0.03), 0, 1))
                feats[f"sev_{d}_180d"] = float(np.clip(0.3 * trend + 0.7 * base + rng.normal(0, 0.02), 0, 1))
                window_severity[d] = feats[f"sev_{d}_30d"]

            feats["poverty_pct"] = poverty
            feats["yield_trend"] = yield_trend
            feats["season_cos"] = season_cos
            feats["season_sin"] = season_sin

            # Ground-truth IPC: nonlinear in weighted severity, modulated by
            # vulnerability and seasonal exposure. Mirrors the impact model.
            disruptor_weight = {"drought": 0.45, "flood": 0.30, "heat": 0.25, "pest": 0.20, "frost": 0.35}
            sev_score = sum(disruptor_weight[d] * window_severity[d] for d in DISRUPTORS)
            vulnerability = 0.4 + 0.6 * (poverty / 100.0) - 0.5 * yield_trend
            # Season amplifies if growing season (Apr–Sep northern bias)
            season_amp = 1.0 + 0.20 * max(0.0, season_sin)
            stress = sev_score * vulnerability * season_amp
            # Map stress→IPC with a smooth sigmoid; clamp to [1, 5]
            base_phase = 1.0 + 4.0 / (1.0 + math.exp(-4.5 * (stress - 0.40)))

            row_base = {"region_id": region_id, "snapshot_date": snap_date, **feats}

            for h in HORIZONS:
                # Forward drift: longer horizon → more uncertainty + slight upward bias
                drift = 0.04 * h + rng.normal(0, 0.05 + 0.025 * h)
                phase = float(np.clip(base_phase + drift, 1.0, 5.0))
                rows.append({**row_base, "horizon_months": h, "ipc_phase": phase})

    df = pd.DataFrame(rows)
    return df


def build_corpus() -> tuple[pd.DataFrame, str]:
    db_df = _try_db_corpus()
    if db_df is not None:
        return db_df, "db"
    return _synthetic_corpus(), "synthetic"


# -----------------------------------------------------------------------------
# Training
# -----------------------------------------------------------------------------
def _train_one(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    X_va: np.ndarray,
    y_va: np.ndarray,
    quantile: float,
) -> tuple[xgb.XGBRegressor, dict[str, float]]:
    model = xgb.XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=quantile,
        tree_method="hist",
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        min_child_weight=4,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        random_state=0,
    )
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
    pred = model.predict(X_va)
    return model, {"val_mae": float(mean_absolute_error(y_va, pred))}


def train_all(df: pd.DataFrame, source: str) -> dict:
    metrics: dict[str, dict[str, float]] = {}
    # Per-horizon split → independent train/val (shuffle by region to avoid leakage)
    rng = np.random.default_rng(0)
    regions = df["region_id"].unique()
    rng.shuffle(regions)
    cut = int(0.8 * len(regions))
    train_regions = set(regions[:cut])
    train_mask = df["region_id"].isin(train_regions)

    for h in HORIZONS:
        sub = df[df["horizon_months"] == h]
        X = sub[FEATURE_COLS].to_numpy(dtype=np.float32)
        y = sub["ipc_phase"].to_numpy(dtype=np.float32)
        mask = train_mask.loc[sub.index].to_numpy()
        X_tr, y_tr = X[mask], y[mask]
        X_va, y_va = X[~mask], y[~mask]

        for q in QUANTILES:
            model, m = _train_one(X_tr, y_tr, X_va, y_va, q)
            path = MODELS_DIR / f"projector_h{h}_q{int(q * 100):02d}.joblib"
            joblib.dump(model, path)
            metrics[f"h{h}_q{int(q * 100):02d}"] = m
            print(f"[train] h={h:>2}mo q={q:.2f}  val_mae={m['val_mae']:.3f}  → {path.name}")

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "n_rows": int(len(df)),
        "horizons": HORIZONS,
        "quantiles": QUANTILES,
        "feature_cols": FEATURE_COLS,
        "metrics": metrics,
        "notes": (
            "Synthetic corpus calibrated to impact-model physics; replace with "
            "FEWS NET-labeled DB corpus once ipc_observations is populated."
            if source == "synthetic"
            else "Trained on DB-derived corpus."
        ),
    }
    (MODELS_DIR / "projector_meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def main() -> None:
    df, source = build_corpus()
    print(f"[corpus] source={source} rows={len(df)} regions={df['region_id'].nunique()}")
    meta = train_all(df, source)
    print(f"[done] wrote {len(meta['metrics'])} models → {MODELS_DIR}")


if __name__ == "__main__":
    main()

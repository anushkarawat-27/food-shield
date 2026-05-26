"""Historical backtest: project IPC phase against the 2017 Somalia drought.

We seed a scenario reflecting the documented conditions of the 2016–2017 Horn-
of-Africa drought (consecutive failed rainy seasons, extreme heat, locust pre-
cursors) for six Somali admin-1 regions, run the trained projector at 3/6/12
month horizons, and compare to the FEWS NET IPC classifications actually
observed during that period.

Sources for ground truth:
  - FEWS NET Somalia Food Security Outlook, June 2017
    https://fews.net/east-africa/somalia/food-security-outlook/june-2017
  - FAO/SWALIM seasonal assessment, 2017
    https://www.fao.org/swalim/

This is a sanity check that the trained models produce plausible severity
ordering, not a rigorous evaluation — the synthetic training corpus is
calibrated to the impact-model physics, not to FEWS NET labels directly.
Real holdout validation lands once FEWS NET ingestion populates
ipc_observations.

Run:  python -m scripts.backtest
Writes: docs/backtest_2017_somalia.md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from simulator.projector import _MODELS, _features_for_region

# Region IDs in this script are synthetic — projector is region-agnostic and
# only consumes the scenario severities + poverty. The names are for display.
SOMALIA_2017 = [
    # (region_id, name, poverty_pct, severities, observed_ipc_jun_2017)
    (101, "Bay",           76.0, {"drought": 0.95, "heat": 0.80, "pest": 0.30}, 4),
    (102, "Bakool",        82.0, {"drought": 0.95, "heat": 0.80, "pest": 0.30}, 4),
    (103, "Lower Shabelle",70.0, {"drought": 0.85, "heat": 0.75, "flood": 0.20}, 3),
    (104, "Mudug",         65.0, {"drought": 0.90, "heat": 0.85},                4),
    (105, "Sool",          68.0, {"drought": 0.90, "heat": 0.80},                3),
    (106, "Banadir",       55.0, {"drought": 0.70, "heat": 0.65},                3),
]


def _project_one(severities: dict[str, float], poverty: float) -> dict[int, dict[str, float]]:
    """Return {horizon: {p10, p50, p90}} using the trained models if loaded,
    else the heuristic fallback."""
    if _MODELS is None:
        # Fallback path; mirror the heuristic in projector.py
        from simulator.projector import _heuristic
        rows = _heuristic(0, severities, [3, 6, 12])
        return {r["horizon_months"]: {"p10": r["ci_low"], "p50": r["ipc_phase"], "p90": r["ci_high"]}
                for r in rows}

    X = _features_for_region(severities, poverty_pct=poverty)
    out: dict[int, dict[str, float]] = {}
    for h in [3, 6, 12]:
        out[h] = {
            "p10": float(_MODELS[(h, 10)].predict(X)[0]),
            "p50": float(_MODELS[(h, 50)].predict(X)[0]),
            "p90": float(_MODELS[(h, 90)].predict(X)[0]),
        }
    return out


def main() -> None:
    rows = []
    abs_err_per_horizon = {3: [], 6: [], 12: []}

    for rid, name, poverty, sev, observed in SOMALIA_2017:
        preds = _project_one(sev, poverty)
        rows.append({"region": name, "poverty_pct": poverty, "observed": observed, "preds": preds})
        for h, q in preds.items():
            abs_err_per_horizon[h].append(abs(q["p50"] - observed))

    # Write the markdown report
    out_path = Path(__file__).resolve().parent.parent / "docs" / "backtest_2017_somalia.md"
    out_path.parent.mkdir(exist_ok=True)
    lines: list[str] = []
    lines.append("# Backtest — 2017 Somalia drought\n")
    lines.append(f"_Generated {datetime.now(timezone.utc).isoformat()}_\n")
    lines.append("Compares trained-projector output against FEWS NET IPC phases ")
    lines.append("observed in Somalia during the 2016–2017 Horn-of-Africa drought.\n")
    lines.append("Model source: " + (_MODELS["_meta"]["source"] if _MODELS else "heuristic-fallback") + "\n")
    lines.append("\n## Predictions vs. observed (June 2017)\n")
    lines.append("| Region | Observed IPC | Pred 3mo (p10/p50/p90) | Pred 6mo | Pred 12mo |")
    lines.append("|---|---:|---|---|---|")
    for r in rows:
        p = r["preds"]
        def fmt(h):
            q = p[h]
            return f"{q['p10']:.2f} / **{q['p50']:.2f}** / {q['p90']:.2f}"
        lines.append(
            f"| {r['region']} | {r['observed']} | {fmt(3)} | {fmt(6)} | {fmt(12)} |"
        )

    lines.append("\n## Mean absolute error (p50 vs. observed)\n")
    for h in [3, 6, 12]:
        mae = sum(abs_err_per_horizon[h]) / len(abs_err_per_horizon[h])
        lines.append(f"- **{h} months**: MAE = {mae:.3f} IPC phases (n={len(abs_err_per_horizon[h])})")

    lines.append("\n## Sources\n")
    lines.append("- FEWS NET Somalia Food Security Outlook, June 2017: "
                 "https://fews.net/east-africa/somalia/food-security-outlook/june-2017")
    lines.append("- FAO/SWALIM seasonal assessment, 2017: https://www.fao.org/swalim/")
    lines.append("\n## Caveats\n")
    lines.append("- Training labels are currently synthetic, calibrated to the impact-model ")
    lines.append("  physics. Replace with FEWS NET-labeled corpus once `ipc_observations` is ")
    lines.append("  populated by the FEWS NET ingestor (see `simulator/train_projector.py`).\n")
    lines.append("- IPC observed values are point estimates from FEWS NET maps and may differ ")
    lines.append("  by sub-district. Districts here are admin-1.")

    out_path.write_text("\n".join(lines))
    print(f"[backtest] wrote {out_path}")
    for h in [3, 6, 12]:
        mae = sum(abs_err_per_horizon[h]) / len(abs_err_per_horizon[h])
        print(f"[backtest] horizon={h:>2}mo  MAE={mae:.3f} (n={len(abs_err_per_horizon[h])})")


if __name__ == "__main__":
    main()

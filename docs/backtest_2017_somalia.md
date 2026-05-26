# Backtest — 2017 Somalia drought

_Generated 2026-05-26T20:11:43.094478+00:00_

Compares trained-projector output against FEWS NET IPC phases 
observed in Somalia during the 2016–2017 Horn-of-Africa drought.

Model source: synthetic


## Predictions vs. observed (June 2017)

| Region | Observed IPC | Pred 3mo (p10/p50/p90) | Pred 6mo | Pred 12mo |
|---|---:|---|---|---|
| Bay | 4 | 2.97 / **3.76** / 4.03 | 3.15 / **3.78** / 4.31 | 3.05 / **4.14** / 4.31 |
| Bakool | 4 | 2.97 / **3.76** / 4.03 | 3.15 / **3.81** / 4.32 | 3.05 / **4.17** / 4.33 |
| Lower Shabelle | 3 | 2.87 / **3.56** / 4.00 | 3.04 / **3.56** / 4.04 | 3.06 / **3.85** / 4.38 |
| Mudug | 4 | 2.64 / **3.41** / 3.71 | 2.87 / **3.51** / 3.79 | 2.77 / **3.82** / 4.18 |
| Sool | 3 | 2.66 / **3.42** / 3.86 | 2.84 / **3.48** / 3.84 | 2.76 / **3.83** / 4.24 |
| Banadir | 3 | 2.45 / **3.01** / 3.44 | 2.64 / **3.15** / 3.56 | 2.68 / **3.60** / 3.85 |

## Mean absolute error (p50 vs. observed)

- **3 months**: MAE = 0.344 IPC phases (n=6)
- **6 months**: MAE = 0.348 IPC phases (n=6)
- **12 months**: MAE = 0.461 IPC phases (n=6)

## Sources

- FEWS NET Somalia Food Security Outlook, June 2017: https://fews.net/east-africa/somalia/food-security-outlook/june-2017
- FAO/SWALIM seasonal assessment, 2017: https://www.fao.org/swalim/

## Caveats

- Training labels are currently synthetic, calibrated to the impact-model 
  physics. Replace with FEWS NET-labeled corpus once `ipc_observations` is 
  populated by the FEWS NET ingestor (see `simulator/train_projector.py`).

- IPC observed values are point estimates from FEWS NET maps and may differ 
  by sub-district. Districts here are admin-1.
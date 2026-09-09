# Package 25 — Staggered-fork H-RAT: R varies 5×, predicts nothing (second honest null)

## Question (pkg20 residue)
H-RAT retrospective was inconclusive because R never varied (~0–0.06 at the single
fork). Stagger fork depth (G4/G7/G10 of a ramp-then-collapse prefix) to vary R with
A matched by construction, and test whether R·A predicts realized gain T.

## Design
Ramp G0–G2 (stratified kept + screened pool → frontier tier_acc[2] 0.864) then collapse
G3–G10 (plain kept + recency pool → 0.925, 0.845, 0.765, 0.685, 0.605, 0.525, 0.445,
0.365 — exactly −0.08/round, the forgetting mechanism dead-on). Recovery +4 rounds per
fork with same-tier golden backfill → poolhard=12, phc=1.0 every round, all forks
(A=1.0 zero-variance by construction). R from live ledger rebuild at each fork:
−0.063…0.333 (5× range). T over three recovery trainings, probe primary (rematch
doctrine). 9 points. `python flywheel_pkg25.py` → `pkg25_hrat.json`.

## Method incident (kept, instructive)
v1 used greedy by-score golden backfill and got poolhard=0 everywhere (hard-golden
scores run lower; top-12 backfill took easy+med only) — A matched at ZERO, arms kept
collapsing. Fix: tier-aware backfill (pkg23 doctrine: backfill only empty tiers, same
tier). Pool-construction details can silently void a design; the per-round poolhard
assert is now load-bearing instrumentation.

## Result: R·A reduces to R, R correlates with T_train spuriously, T_probe null

| stat (n=9) | value | read |
|---|---|---|
| Pearson(R, T_train) | 0.574 | spurious (see next line) |
| Pearson(start, T_train) | **−1.000** | T_train is a deterministic function of fork start (ceiling−start); all arms converge ≈0.9–0.96 |
| Pearson(R, start) | −0.574 | R = frontier−start shares the start term → R–T_train correlation by construction |
| Pearson(R, T_probe) | **0.133** | no detectable contribution of regret depth to held-out gain |
| T_probe by depth | shallow [0.19, 0.06, 0.00], mid [0.25, 0.44, 0.62], deep [0.69, 0.31, 0.12] | inconsistent direction across seeds; mid/deep lead alternates |

## Doctrine delta
- **H stays parked, harder.** Even with proper R variation and matched A, regret depth
  adds nothing detectable to probe gain. Any future regret↔gain correlation must control
  for fork start — R and T share the start term whenever both derive from current-vs-
  frontier/ceiling, so naive Pearson(R·A, gain) (pkg20's 0.53 included) is suspect by
  construction, not just underpowered.
- T is fixed to the probe endpoint (rematch rule holds: T_train is headroom arithmetic).
- Candidate confound logged, untested: deep-fork models lose easy/med scaffolding too,
  which may explain mid>deep on 2/3 seeds — needs a scaffold-matched design, not claimed.

# WQ1 — Contribution-type taxonomy instrument: PASS (84/84, zero recombine)

## Instrument (`tools/contrib_taxonomy.py`)
Per-slice parent→child classifier: preserve / amplify / discover / recombine /
drift / dormant / degrade (+ evaluator axis specified, uncalibrated — judge_corr flat
in all runs consumed so far, per WQ3 condition). Thresholds EPS=0.02, DELTA=0.05,
FLOOR=0.35, HIGH=0.60, CEIL=0.90. Capability proxy: batch tier_corr for cross-arm
same-round comparisons; model tier_acc params for within-arm transitions (params are
the denoised state — batch wobbles of 0.05–0.08 trip DELTA without capability loss;
conversely params move ~0.01/round so param-level classes skew preserve — use batch
for magnitude, params for direction).

## Validation on known answers
- P1 pkg24 merged-G4 vs single-G4 (same E-only pool, E+W vs E parents): 6 degrade,
  3 drift, 0 amplify, **0 recombine**. Pure weight change never improves.
- P2 pkg21 merged-G4 vs single-G4: mostly degrade/preserve/drift + 2 amplify
  (s0-t1 both arms). The amplifies are pool-channel gains (H practices med, so the
  weak-parent condition correctly fails) — consult-compatible, not P0 hits.
- P3 pkg26: single==pruned classes identical; polluted G4→G5 t1 degrade all seeds.
- P4 pkg24 single-arm param transitions: 18/18 preserve, 0 degrade.

## Doctrine consequence (the consult distinction, operationalized)
amplify = pool-channel gain (capturable by retrieval; needs one good parent) vs
recombine = weight-level joint accessibility (needs both parents + weak-other-parent).
The classifier reproduces the whole doctrine mechanically: pkg21-s0 shows amplify
without recombine (pool win, retrieval-bound — consult), pkg24 shows degrade without
amplify (weight pollution). **Recombine has never fired in any run to date.**
Condition B (recombine hit → P0 incident) not triggered. WQ2/WQ4/WQ5 UNLOCKED.

## Limits (honest)
- batch tier_corr proxy: sampling noise near thresholds (drift bucket absorbs most).
- discover class untested (no lineage-novel capability exists in any consumed run —
  expected; discovery needs the heterogeneous/open regimes of WQ4/WQ5).
- evaluator axis uncalibrated (flat inputs).

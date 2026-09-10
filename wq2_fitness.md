# WQ2 — Parent-fitness gate: PASS on EV (+0.046/cell)

## Gate (`tools/fitness_gate.py`, router-usable at fork time)
UNFIT iff `veto_override` (merged with pair_gain ≤ 0.05) or `tainted_history`
(a veto existed and the arm's training history still carries the vetoed branch).
FIT otherwise (pure single, pruned fallback, legitimate gain>gate merges).

## Validation (15 UNFIT cells across pkg21/24/26)
- Directional: 10/15 UNFIT trail FIT-best at G7 med-tier.
- EV: mean(FIT-best − UNFIT) = **+0.046/cell** — the insurance pays on average.
- All 5 counters are seed 3000 (documented washout: contamination fails to
  materialize there; single itself sags to 0.792 while UNFIT arms read 0.812–0.917,
  inside single's cross-seed range — batch noise ±0.06–0.08, mechanism unclaimed).
- pkg21 legitimate merges (gain 0.333) all FIT — the gate does not veto real
  complementarity. pkg26 pruned FIT, polluted UNFIT — matches the exact kill.

## Doctrine consequence
Route away from UNFIT lineages ex ante (prefer FIT; pick best among FIT). s3000-type
washouts are the known price: insurance costs −0.125 there, pays +0.146/+0.062
elsewhere. Router rule ships as stated; revisit only if a regime shows negative EV.

## Status note (round4 audit — binding on router integration)
The gate is a RISK PRIOR, not a detector: it flags fork statistics (veto + history),
not mechanism presence, and cannot by itself detect washout regimes (s3000's fork
statistics matched s0/s1500 while contamination never materialized). Its EV is
regime-dependent by construction. Router integration MUST NOT ride the pooled mean:
carry per-seed EV (+0.104/+0.104/−0.070) into the router doc, keep integration QUEUED
behind WQ2b (measured-pollution flag + taint-decay calibration), and state the
prior-not-detector status wherever the flag is consumed.

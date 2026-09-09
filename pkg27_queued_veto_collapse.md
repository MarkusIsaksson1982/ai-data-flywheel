# Queued: veto-under-collapse stress test (archived, unrun)

## Question
Does the C_pair veto hold when the good branch is collapsing? (pkg24 proved the veto
load-bearing with a healthy E; pkg25 showed collapse dynamics are exactly −0.08/round.)

## Structural read (why this is queued, not run)
gain = pair − best-single over a stale-high lineage denominator. If W contributes
nothing, gain stays ~0 no matter how far E sinks; stale denominator makes the veto
STRICTER (small honest ε from W gets divided down), never looser. Predicted result:
veto holds throughout, conservative bias grows with collapse depth. A run would confirm
a structurally-forced result — measure only if trajectories are wanted on record.

## Design (if picked up)
Fork pkg24-v2 verbatim except E trains under collapse pressure (plain top-18 selection
+ recency-36 pool, so E's med tier degrades G1–G3); W stays invert-zero on hard.
Branch-phase-only package (no arms): endpoint = gate decision (scalar, gain) per round
G1–G3. Falsifier: gain ever > 0.05 (spurious merge with a zero branch) as E sinks.
Secondary: log veto strictness (0.05 − gain) vs E tier_acc slope.

## Explicitly NOT this test
W's quality mismeasured by a broken judge under collapse (invert-inflated wrong arts
scoring high) is a judge-robustness question, not a veto question — do not conflate;
spec separately if needed (poison + collapse interaction, pkg22 × pkg25).

## Preconditions / pointers
- Reuse: `flywheel_pkg24.py` fork block (E_DIET/W_DIET, gates), `flywheel_pkg26.py`
  arm-less branch loop pattern; collapse selection/pool from `flywheel_pkg25.py` prefix.
- Reports: `pkg24_disagree.md` (veto doctrine), `pkg25_hrat.md` (collapse −0.08/round).

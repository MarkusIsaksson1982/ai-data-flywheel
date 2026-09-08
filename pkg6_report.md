# Package 6 report — Reference-augmented stopping rule + real revert-and-continue

6 revert runs (R1/R2 × 3 seeds, forked from live-detected collapsed prefixes) +
post-hoc rule trial over all 12 pkg4 trajectories. Data: `pkg6_revert.json`.
Rule (live): fire iff probe < pooled-healthy-ref − 0.15 (reference breach) OR
self-history 10pt probe drop with main holding.

## Q1. Fire by G1 with residual ≥ 0.6? No on both counts.

Live fires: G3 / G2 / G2, every one via the reference trigger (the drop trigger
never fires first). Checkpoint residuals (pre-warning model round): 0.306 /
0.306 / 0.361. The augmentation fixes the miss problem (9/9 pkg4-comp
trajectories fire post-hoc, vs 6/9 for self-history alone, earlier-or-equal) —
but no rule can fix checkpoint weakness, because damage starts at G0 (growth
hits generation immediately). There is a fundamental earliness–residual
tradeoff: the only G1-firing signal found (keptlen > 2.0: 2.06+ on all comp vs
≤1.67 on all controls) would roll back to M_0, the weakest checkpoint of all.
Earlier detection ⇔ weaker checkpoint, when degradation is congenital.

## Q2. Does revert-continue restore the healthy trajectory? No.

Finals (main): R1 0.528/0.472/0.417, R2 0.528/0.472/0.500 — recovery bar 0.65
unmet on all 6 runs; R1 ≡ R2 (soft penalty redundant once selection is
repaired). Best observed recovery remains pkg5-B forward treatment (0.70).
Counter-intuitive but evidence-backed: rolling back to the *earlier, cleaner*
checkpoint does WORSE than treating forward from the collapsed state, because
rollback discards archive richness (18-art pools at fork vs full 36) while the
environment flaw persists either way. **Don't roll back; treat forward.**
Revert machinery is demoted to insurance (checkpoint retention stays cheap).

## False positives: 0, but the margin is thin.

Max healthy deviation below reference: 0.139 (control-s3000 G2) vs 0.15
threshold. The rule holds on current data with ~0.01 to spare at the closest
approach — adopt with a calibration warning: re-fit the 0.15 constant against
a wider healthy reference before trusting it operationally.

## Provenance caveat (documented, contained).

The pkg6 prefix differs from pkg4 comp80 by one G0 artifact (0.333 vs 0.361;
probe identical). Current-code determinism verified bit-identical across
reruns, so this is a base-file micro-edit between turns shifting one RNG
decision, not nondeterminism. Fork validity is unaffected (arms share the
prefix bit-identically); cross-turn bit-identity now carries a fingerprint
requirement, which this report establishes going forward.

## Decisions.

- ADOPT the reference+drop rule as a tripwire (fires G2–G3, 0 FP with noted
  margin); REJECT it as an auto-revert trigger (checkpoints too weak to justify
  rollback — and rollback underperforms forward treatment anyway).
- On fire, the prescribed response is forward length-regularized retraining
  (pkg5-B style), never rollback.
- Next question, single and now well-posed: does the same rule + response
  close the loop on a *fresh* failure (misc-style lock-in under a repaired
  judge), i.e. is "reference tripwire → forward regularized treatment" a
  general incident-response playbook, or compounding-specific?

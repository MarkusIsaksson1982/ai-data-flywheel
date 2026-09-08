# Realism jump report — Gradient flywheel: qualified transfer, one law evaporates

9 runs (3 arms × 3 seeds, 6 rounds; ~700-param tanh MLP, full-batch GD on
log-targets, procedural arithmetic bank + fresh-seed probe). Data:
`lm_transfer.json`. Two methodological nulls on the way (additive corruption
invisible after log transform; NaN from non-positive claims) are documented in
code comments — both fixed, rerun green.

## Transferred intact.

- Gating machinery: agreement ≈ −0.995 fires alpha 0.8 on every invert round;
  gated endpoints ≈ control on all slices (hard 2.3M vs 2.0M, med slightly
  better) — containment holds under gradients.
- Probe tracks test in all arms (no memorization gap); loop deterministic.
- Inversion degrades hard slice selectively (~5×: 9.8M vs 2.0M) while easy/med
  hold — quality collapse exists but is slice-selective, not global.

## Evaporated: bottleneck conservation as a predictive law (r ≈ −0.03).

Pool clean-mass (0–5 invert vs ~80 control) does not predict per-slice gains,
in any arm. Mechanism: heuristic blending moves TOWARD pool traits (mass gates
learning), but full-batch GD averages them — unbiased-ish multiplicative noise
still teaches the central tendency (invert mean gain even exceeds control's:
0.056 vs 0.038). The r=0.70 law carries a scope condition the sim never
revealed: it holds for distillation-style updaters, not gradient averaging over
noisy targets. Counts without correctness still move nothing anywhere — but
noisy correctness moves plenty under GD.

## Decisions.

- Adopt the gradient harness as the transfer testbed (it runs); keep the sim
  as the primary theory substrate (laws are sharper there).
- Single next run if any: systematically-BIASED poison (always-×2 targets,
  non-zero-mean noise that cannot average out) — separates "gradients tolerate
  label noise" (shown) from "gradients tolerate poisoning" (untested). Do not
  expand scope beyond that one comparison.

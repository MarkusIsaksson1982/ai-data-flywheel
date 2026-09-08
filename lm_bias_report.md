# Biased-poison report — Gradients tolerate noise, not coordinated poisoning

3 runs (bias arm × 3 seeds; always-×2 corruption, invert selection+targets).
Data: `lm_bias.json`. Comparators in `lm_transfer.json` (G5 means over seeds).

## G5 test MSE by arm: easy / med / hard.

control 533 / 27k / 2.0M · invert 527 / 28k / 9.8M · gated 500 / 23k / 2.3M ·
**bias ~950 / ~460k / ~45M** — ~2× / ~17× / ~20× worse than control on every
slice, ~5× worse than invert on hard. Coordinated (non-zero-mean) poison
collapses performance GLOBALLY, including easy slices the unbiased arm spares:
shared weights propagate the bias everywhere. Clean pools sit at ~0 throughout
(vs ~80 control), so the bottleneck law has nothing to bite on — correctly, per
its scope condition (no correct mass ⇒ no learning; here the failure is active
misteaching, not missing mass).

## Verdict: the evaporation was about mean-preservation, not averaging per se.

Unbiased multiplicative noise (geometric mean ≈ 1) teaches the central tendency
and degrades hard-only ~5×; systematic ×2 bias (log-shift +0.30 that cannot
average out) breaks all slices 2–20×. Under gradient descent, the load-bearing
distinction is noise vs bias in the training targets — the sim-side margin rule
reappears in translated form: unbiased deviations are absorbed (same qualitative
role as below-gap proxies), systematic deviation compounds (same role as
gap-exceeding/inverting judges). Gating was not re-tested here (prior containment
result stands for the noise regime); the open follow-up is whether gated mixing
contains always-×2 (predict yes: 0.8 weight on true targets bounds bias to 20%).

## Confirmation: gating contains always-×2 (run after, `lm_gatedbias.json`).

gatedbias arm (invert judge + gated 0.8 mixing + ×2 corruption), 3 seeds:
agreement −0.995 fires alpha 0.8 every round; selected pools stay ~80+ clean per
slice (0.8·rule ranking sees through inversion); 20%-poisoned training targets
cause no measurable damage. G5 test MSE means — easy / med / hard: control
533/27k/2.0M · bias ~950/460k/45M · **gatedbias ~490/23k/2.1M**, i.e. containment
to control levels (≈20× better than the bias arm on hard). Disclosure of a
caught misrun: the first gatedbias attempt silently ran a faithful judge
(exact-string tuple membership missed the new arm name), producing a control
duplicate; caught on the agreement readout (+0.995 instead of −0.995), fixed
with a one-line tuple addition, rerun green. Containment now holds in both
regimes — unbiased noise (prior) and coordinated ×2 bias (here) — and the
gradient-harness transfer file is closed.

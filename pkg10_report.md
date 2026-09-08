# Package 10 report — Tier-specific skills: data composition MATTERS (scope boundary broken)

6 combos (2 arms × 3 seeds, 6 rounds, 48-problem procedural bank). Data:
`pkg10_tierskills.json`. Base sim carries guarded tier_acc (learn own-tier,
forget unpracticed toward 0.30); legacy paths bit-identical.

## Plain top-k produces genuine hard-tier capability collapse.

Hard-tier corr G5 under plain: 0.167 / 0.208 / 0.021 (from ~0.3), tier_acc
pinned at the 0.30 floor from G3 while easy acc hits 0.977 — while easy-tier
corr reaches 0.94–1.0 on the SAME models. This is capability amputation, not
data skew: the numbers obey the multiplicative model (0.30^3.5 ≈ 0.015 ≈
observed 0.021). pkg9's null is overturned exactly where predicted: with
non-transferable skills, unpracticed capability decays.

## Stratification rescues it — partially, consistently, generalizing.

Hard-tier G5 strat minus plain per seed: +0.229 / +0.167 / +0.333 (mean
+0.243, consistent sign, ≫ seed noise ±0.08). Overall corr +0.106. Held-out
probe-hard gap is largest: +0.250 / +0.125 / +0.500 (mean +0.292) — the rescue
generalizes to unseen hard problems, ruling out bank overfitting. Rescue is
partial (hard 0.35–0.40 vs easy 1.0): hard kept are low-quality, so hard acc
learns slowly (0.62–0.77) — quotas buy practice, not mastery.
Easy tier pays nothing (plain 0.972 vs strat 0.986): the Thread-C dilution
worry is falsified here — easy skill saturates regardless of quota diversion.

## Scope verdict.

The shared-skill regime is NOT the platform's scope boundary: introduce
non-transferable skills and data composition drives capability (±0.24 on hard,
±0.29 held-out). The Thread-C nulls are now bounded precisely — reuse policy
is irrelevant if and only if skills transfer fully; with forgetting
un-practiced skills, quotas are load-bearing. Standing recommendation updates:
(1) keep recency-36 default where skills transfer (unchanged); (2) ADD a
transfer diagnostic to the frozen suite — if per-tier/per-slice learning curves
diverge (tier_acc spread or slice-corr gaps growing), switch selection to
stratified quotas; (3) dilution monitoring stays (no cost observed, tripwire
retained). Next single question: does the same hold under collapse pressure
(stratified recovery from a hard-tier floor), or does the quota merely slow
the fall when data is scarce?

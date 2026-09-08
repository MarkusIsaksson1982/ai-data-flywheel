# Package 13 report — Capability-conditioned valuation: works, ties simpler rival

9 + 9 runs (3 pool policies × 3 seeds × starved/banked prefixes). Data:
`pkg13_value.json` (starved; all arms identical), `pkg13_value_banked.json`.

## Starved prefix: valuation is moot without banked data (structural finding).

Under plain selection the archive contains ZERO hard-tier artifacts (0 hard
kept in every prefix round, all seeds) — so recency, scalarU and condU train on
identical pools and finish identically (acc stuck 0.3). Archive valuation can
only re-weight what selection banks. Selection quotas are the archiving
mechanism; valuation operates downstream of them. This bounds the whole
valuation question before answering it.

## Banked prefix: conditional valuation works — and ties the simpler rival.

With hard data banked (stratified prefix), recovery G9 hard-acc: recency
0.30–0.45 (decays as window slides past), scalarU 0.92–0.95, condU 0.83–0.92.
Pool hard-correct rate is 1.0 everywhere, both policies, all rounds — both
retrieve exclusively correct hard arts; quality never differs, only quantity
and timing do. Mechanisms differ as designed: condU takes all-hard pools while
deficit is extreme (w_hard 0.92–0.95, 36/36) then TAPERS as it closes
(w 0.57→0.29, pools 36→8) — self-tuning verified live, including the crossover
where hard stops being neediest; scalarU accumulates steadily (12→23) via
static need+novelty. The taper has one measured cost: s3000 G8 chases a medium
dip (w_med 0.54, poolhard 0) and ends slightly lower (0.825 vs 0.948).
Calibration: within-run mean-U vs next hard-gain r≈0.7 — valid as a priority
signal (high U = large remaining headroom), confounded by saturation as a gain
estimator; Thread C's cross-sectional null is not overturned, only scoped.

## Verdict: adopt the cheap one, keep the conditional one for shifting deficits.

No outcome difference between scalarU-need and condU here → recommend static
need+novelty as the default archive policy (simpler, no live-state dependency,
same recovery). Adopt conditional deficit weights where deficits move or hard
data is costly (it uses fewer hard items late for equal skill: efficiency win),
with the s3000 chase noted as the failure mode to watch (hysteresis/damping on
w would fix it — specified, not run). Recency stays the calm-regime default;
valuation engages on detected forgetting. Next single question per brief ladder:
compositional failure (forgetting + misconception together) to test whether the
diagnosis library — need-weights, misc-channels, probe — selects this response
for the right reason.

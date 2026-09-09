# Package 20 report — Regret-weighted import: matches binary, never beats it

9 runs (3 pool policies × 3 seeds, forked from banked prefixes; selection fixed
plain top-18 to isolate pools). Data: `pkg20_regret_banked.json` (+ a
`_starved` control set documenting the banking precondition, kept for method).
Live ledger rebuild per round worked every round (deficit weights correctly
concentrated on tier-2: w→1.0 and stayed there until recovery, then tapered).

## G9 hard-acc: binary [0.924, 0.924, 0.948], regret [0.924, 0.782, 0.948], recency floored.

Graded regret never beats binary forgotten; strictly worse once (s1500, where
deficit-chasing swung weights to tier-1, pool-hard hit 0 at G8, and acc ended
0.782 vs 0.924). Combined with pkg13 (conditional-U ties scalar-U): utility
sophistication consistently adds nothing over a binary need flag. The deficit
oscillation seen here and in pkg13 is a real failure mode of adaptive weights,
not noise — static need does not hunt.

## H-RAT retrospective: inconclusive as operationalized (honest null).

R measured at fork is ~0–0.06 everywhere (collapse just began; frontier holder
≈ current), so R·A reduces to A and Pearson(R·A, gain)=0.53 is carried entirely
by pool-correct-mass differences — i.e. the bottleneck result again, with no
independent contribution from R detectable. Testing R's contribution properly
needs staggered fork depths (variation in R independent of A): specified, not
run. T remains outcome-only by construction.

## Residue worth one line.

Probe-hard favors regret on 2/3 seeds (0.75/0.812 vs 0.562/0.625; tie on s0)
despite lower train acc on s1500 — consistent with novelty/diversity in the
regret pools acting as regularization. If the objective is held-out hard
capability rather than train-skill restoration, regret deserves a rematch with
probe-hard as primary endpoint; as a recovery policy it stays second choice.

## Verdict: keep binary-forgotten; regret weights stay diagnostic.

Regret computation ( adopted consumers) is validated as a *detector* (correct
tier flagged every round); as a *selection signal* it adds nothing over binary
need and introduces hunting. Recommendation: binary need flag for pools,
regret trajectories for monitoring, H in R·A·T form parked until staggered-depth
data exists.

## Doctrine lock (pkg21/22 priors).

Complementarity (pkg21) and dose scheduling (pkg22) are to be tested against
the same BINARY baseline established here — not against graded regret, which
this package retires as a selection signal. Any challenger must beat binary
need on recovery endpoints; diagnostic instruments (regret trajectories, NDS)
stay read-only.

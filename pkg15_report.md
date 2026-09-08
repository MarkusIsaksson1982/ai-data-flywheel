# Package 15 report — Asymptote reached; bottlenecks made infrastructure

## (a) Matched-response asymptote: full restoration, no sub-healthy plateau.

Extended A/D to G11 (G7 identity gates vs pkg14 passed on all seeds — third
cross-turn replication). Hard acc2: D 0.959 / 0.966 / 0.964 by G11 (healthy
easy-tier band 0.977; restored, not plateaued); A pinned 0.351–0.353 on all
33 arm-rounds (forgetting-floor equilibrium). Hard corr trails skill
(0.48–0.58 vs acc 0.96 — multiplicative chains), probe-hard reaches
0.56–0.75. The pkg14 open is closed as full recovery given ~6 rounds from
fork: matched response restores, single fixes stagnate.

## (b) Bottleneck accounting, validated: `flywheel_bottleneck.py`.

Per-round capability mass (correct-hard counts) through generation → kept →
pool, joined to next-model Δacc2 across pkg10/11/12/14/15 (n=327 training
transitions; pkg12 pools logged directly, rest recomputed with documented
builders): **Pearson(pool-correct-hard, Δacc2) = 0.70**; x==0 → mean Δacc
−0.032 (stagnate/forget) vs x>0 → +0.14. Diminishing returns are immediate
(0<x<6 and x≥6 buckets identical at +0.14): ANY correct slice-mass flips the
sign; the lr, not the mass, sets the rate. The module ships the conservation
law as code: what trains the next model is pool CORRECT mass per slice —
counts without correctness (pkg15-A pools held 15–29 wrong hard) move nothing.
Adopt as infrastructure: log G/S/P masses per round by default; alert when any
slice's pool-correct mass hits zero (that is the pkg11-B/A boundary, now a
tripwire condition rather than a post-hoc discovery).

## Standing state.

Incident doctrine unchanged (all replications green). New defaults from this
package: matched-response horizon ~6 rounds to full restoration; bottleneck
masses as first-class logged quantities with the x==0 alert. Next single
question: compositional blanket — forgetting + misconception + inversion at
once — to test whether the diagnosis library routes three simultaneous
channels without a combinatorial procedure.

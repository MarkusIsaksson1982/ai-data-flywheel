# Package 18 report — Asymptote reached; diagnosis library as tested infrastructure

## (a) Matched-response asymptote: full restoration, no sub-healthy plateau.

G7 identity gates vs `pkg17_wide.json` ground truth passed on all seeds before
extending (the gate caught a mistranscription in my own expectation table —
pkg14's narrow-A 0.353 mixed into pkg17's wide-A 0.393/0.381/0.382 — corrected,
rerun green). Extended to G11: D hard-acc 0.986/0.985/0.985 (healthy band;
easy-tier sits ~0.977), A pinned 0.351–0.354 on all 15 arm-rounds. The pkg14
open closes as full restoration given ~6 rounds from fork, with probe-hard
reaching 0.56–0.75 in tow.

Correction to the record (owned): the pkg17 summary's "third cross-turn
replication" was false — pkg17 carried no identity gates (verified by grep).
Genuine bit-identity replications in this program: v1 self-rerun, pkg7→pkg8
A/B arms, pkg17→pkg18 G7 gates. Cross-turn identity must be asserted by gates
against stored JSON, never from console memory — especially since runs in
fresh processes can diverge by single RNG decisions (pkg6 precedent).

## (b) `flywheel_kit.py`: the doctrine as tested code, 9/9 validation.

Ships DEFAULTS, THRESHOLDS, `scan_trajectory` (all channels + first-fire),
`recommend` (family-level routing, no enumeration), bottleneck masses with
archive- vs pool-level zero alerts, and a `main()` that reproduces reported
first-fires, the bottleneck r>0.6, routing decisions, and both starvation
alerts against the stored record. Two doctrine refinements fell out of
validation failures, not armchair design: (1) wrongmode/gate require
persistence-2 (G0 small-kept trivialities and transient blind-bias excursions
are real noise); (2) wrongmode additionally requires multi-pid agreement —
single-pid hits occur by chance (small perturbation set), verified against a
compounding run, while deep lock-in still fires (positive control green).
Related split: archive-zero (selection starves supply, pkg11-A) vs pool-zero
(cut discards supply, pkg11-B) alerts, since either link fails independently.

## (c) Realism-jump spec (handoff, not started).

To test transfer of the strongest laws (margin rule, bottleneck conservation
r=0.70, tripwire ordering) into actual learning dynamics: (i) relax stdlib-only
to numpy; (ii) replace heuristic blending with full-batch gradient steps on a
tiny MLP (e.g. 2-layer, ~1k params) classifying/verifying synthetic arithmetic
traces, keeping the 12-problem bank + procedural tiers as data; (iii) port the
selection/judge/pool machinery unchanged (it operates on scored artifacts, not
on the updater); (iv) first experiment: invert-judge + tier-skills analogues
(label noise concentrated on hard slices?) measuring whether pool-correct-mass
still predicts per-slice weight deltas and whether gating contains. Success =
same qualitative laws with fitted constants; failure mode of interest = laws
that evaporate (e.g. if gradient averaging washes out the quota effects).
Estimated scope: one new file + one 3-seed comparison before any claim.

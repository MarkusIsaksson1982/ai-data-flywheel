# WQ3 — Judge-margin tripwire: design + zero-compute validation (PASS 27/27)

## Rule (`tools/margin_tripwire.py`)
Over KEPT arts per round: signed gap G = mean(judge_score − rule_score).
TRIP iff G > +10 for ≥2 consecutive rounds (hysteresis per rematch doctrine).

## Validation (stored runs, no new compute)
- pkg22 (invert judge, 9 combos): gaps +25…+68, TRIP 9/9.
- pkg20 (blind, 9 combos): gaps −0…+1.7, trip 0/9.
- pkg26 (blind, 9 combos): gaps ±0.0, trip 0/9.
Separation 27/27 with a 10×+ margin between regimes. No tuning was needed — the
+10 band sits in a genuine empty zone, not a fitted boundary.

## Secondary signal (free): margin tracks recovery
pkg22-C gaps fall as screened pools return (s0: 67→42→25; s1500: 63→51→48) while
A/B stay pinned ~63–68. Signed kept-gap is a recovery meter, not just a fire alarm.

## Doctrine consequence
Log signed kept-gap per round everywhere (pkg28 already logs abs margins; signed is
the tripwire form — amend ongoing harnesses to signed). WQ3 condition SATISFIED:
cross-tier judging in pkg28 produced flat margins (~1.0, no triggers) exactly as this
validation predicts for clean regimes — the instrument is calibrated at both ends
without a single new run. Gaming-stress calibration (adversarial judges) remains the
open half; needs poison runs, queued behind WQ5.

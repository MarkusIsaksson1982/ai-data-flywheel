# Package 20 rematch — probe-hard primary with hysteresis (zero-compute reanalysis)

## Question (pkg20 residue)
Train-primary verdict was binary ≥ regret everywhere (G9 hard-acc binary
[0.924, 0.924, 0.948] vs regret [0.924, 0.782, 0.948]). But probe-hard favored
regret on 2/3 seeds at G9 — does a probe-hard primary with a persistence
hysteresis flip the verdict? Rule: regret lead > 0.05 band for ≥2 consecutive
arm rounds. Source: `pkg20_regret_banked.json` (recency/binary/regret × 3 seeds).

## Result: one decisive flip, one tie, one flicker — doctrine stands, endpoint rule added

| seed | train G9 (bin vs reg) | probe G9 (bin vs reg) | gaps G6–G9 | hysteresis |
|---|---|---|---|---|
| 0 | 0.924 / 0.924 | 0.562 / 0.562 | 0, −0.06, 0, 0 | tie |
| 1500 | 0.924 / 0.782 | 0.562 / **0.750** | 0, −0.13, +0.06, +0.19 | **regret wins (run=2)** |
| 3000 | 0.948 / 0.948 | 0.625 / 0.812 | 0, +0.06, −0.06, +0.19 | flicker (run=1), no verdict |

1. **s1500 dissociation**: train −0.142 AND probe +0.188 for regret vs binary —
   train-acc and held-out hard capability move in OPPOSITE directions under
   adaptive pools. The deficit-hunting that wrecks train restoration (pool-hard
   hit 0 at G8) acts as regularization for generalization. No aggregate endpoint
   sees both; reporting train alone actively misleads here.
2. **No general reversal**: regret wins probe-hard on 1/3 seeds under hysteresis,
   ties one, flickers one. "Binary need for pools" STANDS as the selection rule.
3. Same moral as pkg24 (judge gates on practiced-tier deltas, not aggregates):
   the endpoint chooses the winner — binary on restoration, regret competitive
   on generalization via the s1500 pattern.

## Doctrine delta
- Recovery policies must be judged on **held-out probe-hard trajectories**, never
  train restoration alone; require band+persistence hysteresis before calling a
  probe win (G9-only reads flicker — s3000).
- Train/probe dissociation (opposite signs) is now a monitored flag: when it
  appears, the pool is regularizing, not restoring — route to the generalization
  track, not the recovery track.
- H-RAT's T remains outcome-only; this rematch is more evidence that T must be
  fixed to the probe endpoint before R·A·T can mean anything (queued: staggered
  depths for R).

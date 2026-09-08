# Package 14 report — Compositional failure: diagnosis must match both channels

12 runs (4 arms × 3 seeds; prefix: invert + plain + tier skills; fork G5–G7).
Data: `pkg14_comp.json`. Tripwire first-fires: poolhard0 at G0, jcorr (≈−0.99)
+ hard-divergence at G1 — both channels identified by G1.

## Only the matched response moves; each single fix fails distinctly.

G7 hard-acc (acc2) by arm, seeds 0/1500/3000:
A 0.353/0.353/0.353 · B 0.46/0.30/0.353 · C 0.353/0.353/0.353 · D 0.551/0.627/0.602.
Hard corr: A 0.17–0.29, B 0.19–0.33, C 0.17–0.29, D 0.19–0.44. Probe-hard: D
0.25–0.44 vs 0.06–0.31 elsewhere.

- A locked both axes (quality collapsed + hard floored). C ≡ A effectively:
  quotas filled with invert-selected WRONG hard (kept-hard corr 0.0 every
  round) train wrongness — predicted harm direction, null magnitude (pinned,
  not worsened).
- B (judge fix only) does not recover quality: gating contains inversion
  prophylactically (v4), but remedially the models are already degraded
  (all-tier accs fell: easy 0.83→0.66 at G4) and hard stays starved. Judge
  repair without data repair stalls (best G7 hard 0.33, acc 0.46).
- D (gated + quota selection + quota pool) is the sole mover: kept-hard corr
  1.0 throughout, acc 0.37→~0.6 on all seeds, probe-hard best on all seeds.
  Partial (healthy 0.9+ not reached in 3 rounds) but the only positive slope.

## Bonus discovery: score-scale contamination across judge switches.

B/D G5 pools contain 12–17 hard arts ranked by STORED finals — but those finals
were minted under the invert judge (~70 for wrong-hard) and are incommensurable
with blind scores. Pools spanning a judge switch must be RE-SCORED under the
current judge (or ranked by rule); D recovered anyway as blind-scored rounds
flushed the pool by G7, but the G5–G6 training step drank contaminated data.
Adopt as doctrine: any judge change invalidates stored selection scores.

## Verdict: diagnosis matching generalizes to compositional failure.

Neither fix alone suffices (B stalls on degraded generation + starvation; C
trains invert-selected wrongness); the matched pair is the unique positive.
The incident-response doctrine now reads: tripwire suite (first-fire-wins) →
match EVERY firing channel (judge gate + pool quota jointly here) → re-score
pools whenever the judge changes. Next single question: D to asymptote (does
matched response fully restore 0.9+ given 3 more rounds, or plateau?).

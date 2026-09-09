# Package 24 — The disagreement case: scalar fires, per-slice vetoes, veto wins

## Question (pkg21 residue)
Scalar pid-gate and per-slice C_pair gain agreed in every observed fork, so the
veto was never load-bearing. Force the disagreement and see which rule is right.

## v1 post-mortem (preserved as `pkg24_disagree_v1_fallback.json`)
`tC._jaccard` returns `1-|A&B|/|A|B|` — a DIVERGENCE, not an overlap. The v1
same-curriculum pid-matched design scored scalar 0.14–0.27 and vetoed everywhere:
a failed disagreement, but with a serendipitous finding — both fallback arms
underperformed pure single at G7 in 2/3 seeds (s0 med 0.875 vs 0.917, s1500 med
0.833 vs 0.958), because fallback keeps training G5+ on pools containing the
vetoed branch's history (invert-inflated scores rank its wrong arts high).
Fallback-hygiene gap: vetoing weights while keeping the vetoed history in the pool.

## v2 design (this file's run)
Disjoint curricula: E (strong) on easy+med blind-selected correct; W (poisoned
teacher of unseen material) on hard invert-selected confident-wrong (keptcorr 0.0
all rounds, all seeds). Fork, all seeds: **scalar=1.0 FIRES, gain=0.0 VETOES**,
cE={0:1,1:1,2:0}, cW={0,0,0}. The disagreement materialized exactly as designed.

## Result: the veto was load-bearing — scalar-only gating is dead standalone

G7 med-tier (practiced tier; easy at ceiling, hard at floor in all arms):

| seed | single (E) | scalar (merged E+W) | slicemerge (fallback) |
|---|---|---|---|
| 0 | 0.917 | **0.771** (−0.146) | 0.771 |
| 1500 | 0.958 | **0.812** (−0.146) | 0.896 |
| 3000 | 0.792 | 0.812 (+0.020~noise) | 0.917 |

1. **Merging a zero-quality branch hurts** (−0.15 med-tier, 2/3 seeds, immediate G4
   drop with no recovery to single's line). Scalar fired on pure coverage-divergence
   with zero quality complementarity — exactly the case the veto exists for.
2. **Pollution traveled through parent weights, not the pool.** The scalar merge pool
   contained ZERO W arts (Wshare=0.00 all seeds — E's blind-scored correct outrank
   W's invert-scored wrong, closing the pool channel), yet merged weights still lost.
   Weight-averaging a degraded parent ([0.59,0.59,0.39]) drags the practiced tier
   down even trained on clean data.
3. **Fallback arms inherit the v1 hygiene gap** (s0/s1500 below single; s3000 above on
   med but below on hard — mixed, second-order). Prune vetoed-branch history on
   fallback; untested micro-fix, queued.

## Doctrine delta
- Gate rule: **never merge on divergence alone; require gain>0.05** (C_pair veto is
  load-bearing, not decorative). Scalar-only gating is removed from the doctrine.
- Program-level, with the consult null: merging weights adds nothing when branches
  agree (consult: +0.013/0.000/−0.023 novel-acc) and hurts when they disagree
  (pkg24: −0.15). In this regime weight-merging is all downside, no upside —
  harvesting works through pool composition (pkg23, pkg17-D), never weight surgery.
- All failures concentrate in the practiced middle tier; ceilings/floors hide gate
  mistakes. Judge gates on practiced-tier deltas, not aggregates.

## Repro
`python flywheel_pkg24.py` → `pkg24_disagree.json` (3 seeds × fork + 3 arms × 4 rounds).
v1 fallback accident: `pkg24_disagree_v1_fallback.json`. Block `"disagree"`.

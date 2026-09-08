# Thread-C report — Lineage, Archive Value & Multi-Parent Reuse

33 combos across 4 blocks (`threadC_{c_normal,c_collapse,c_parents,c_misc}.json`),
all on frozen DEFAULTS (v4 scorer, blind gated097, misc 0 unless noted), seeds
0/1500/3000, pools capped at 36 (matched budgets). Current-batch selection fixed
to top-18 so differences isolate *reuse* (training-pool) effects.

## Q1. Which history to re-import? In calm regimes: it barely matters.

- Normal G5 means over seeds: recency 0.703, topk_hist 0.713, utility 0.685
  (spread 0.03 ≈ seed noise). Light-collapse recovery: all policies rec=1 with
  near-identical margins. Archive-usage histograms differ starkly — recency
  draws R0 140× vs utility 229× and topk_hist 190× — yet outcomes match.
  Under a faithful judge and clean data, training is robust to pool composition;
  the archive is insurance, not fuel.
- Utility calibration is null: mean pool quality vs next-round gain r = −0.08
  (n=36). The utility score does not predict downstream benefit — gains are
  dominated by generation noise, not pool ranking. Q3 as posed gets a clean
  negative; the score's only live component is the *need* term, untested here
  beyond parity (see recommendation).
- Failure-mode hunt: zero dilution events (pools never score below their
  batches — kept sets are uniformly high-quality under a faithful judge), and
  the predicted "old-data drag" never bites. The real cost is subtler: **archive
  bloat without benefit** — utility/topk_hist lean on R0 for zero gain, paying
  bookkeeping for nothing. Limitation (honest): the light ramp (bottom k=10)
  recovers in 1 round for everyone; reuse differences would need k=6-depth
  collapse to separate (v2 evidence: pre-collapse re-import drove recovery).

## Q2. Multi-parent merging: clean null — needs divergent parents to matter.

G7 means: single_best corr 0.834/cov 0.778, pair_best 0.815/0.778, pair_compl
0.815/0.805. Merging adds nothing (quality −0.02, coverage +0.03 on compl —
noise). Mechanism: observed complementarity only 0.10–0.73 (mean 0.41) — parents
trained on overlapping pools are near-identical vectors, so averaging ≈ either
parent. Multi-parent can only help with *divergent* parents (different seeds,
policies, or objectives — e.g. exploit × explore branches as in base-sim R5,
which did work). Do not merge same-lineage parents; test divergent-parent
merging next, not more same-lineage merging.

## Robustness check (misc 0.15): reuse-independent purge.

Decay curves identical (0.15→~0.03 by G5 both policies); G5 outcomes within
noise of misc-0 controls (0.66 vs 0.70 corr). The rule filter purges mild
contamination whatever the pool builder. No interaction found.

## Recommendation: default lineage policy going forward.

1. **Keep simple recency-36 as the default.** Matches or beats quality-ranked
   and utility-ranked history everywhere tested, cheapest, least stale-data
   exposure.
2. **Size the recency window to cover the pre-collapse baseline** (last 3
   rounds) — v2 showed recovery is driven by pre-collapse rounds; anything
   older adds nothing in these regimes.
3. **Utility-need targeting as a recovery-mode switch only**: when forgetting
   is detected, bias the pool toward absent/weak categories (the one utility
   component with a mechanism); do not run it by default (bloat, no gain,
   uncalibrated scores).
4. **Single parent by default; merge only divergent parents** with a measured
   complementarity gate (e.g. jaccard distance > 0.5), else skip the merge.
5. **Keep tracking**: pool_makeup, archive-usage histogram, mean pool quality
   (dilution tripwire — silent in all 33 runs, which is the point of a tripwire),
   lineage contribution of the final pool.

## Lineage note.

All Thread-C runs log pool_makeup per training, parent_ids + complementarity,
and archive_usage per combo; models carry multi-parent lineage where merged.
Frozen library untouched (one additive base-sim change from v4 predates the
freeze and is covered by bit-identity replication checks).

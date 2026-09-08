# Harness v5 report — worst case, rescue, gap multi-seed, frozen baseline

Blocks: `worst` (4) · `rescue` (prefix + 4 arms × G6–G9) · `gapseed` (12) ·
`baseline` (3, frozen Thread C defaults). Machine-readable:
`harness5_{worst,rescue,gapseed,baseline}.json`.

## 1. Worst case: grid + misconception + invert (comparators: v4 topk in harness4_misc.json)

| combo (grid, misc .35) | G7 corr / cov / misc_rate | topk equivalent |
|---|---|---|
| pure0 | 0.167 / 1.000 / 0.448 | 0.333 / 0.833 / 0.541 |
| fixed05 | 0.611 / 1.000 / 0.024 | 0.472 / 0.833 / 0.106 |
| gated097 | 0.667 / 1.000 / 0.025 | 0.722 / 0.917 / 0.032 |
| pure0, misc 0 (control) | 0.361 / 1.000 / 0.0 | 0.333 / 0.833 / 0.0 |

Grid is the worst case as predicted, but not via deeper quality collapse — via
*masking*: grid+misc+pure0 ends at cov 1.0 with corr 0.167 and kept_misc 0.444.
Full coverage, fluent phrasing, 83% wrong: a healthy-looking corpse that every
coverage/diversity dashboard would pass. Diversity mechanisms preserve
*coordinated* errors across all categories. (Ordering holds at fixed05/gated
too: grid keeps more misc than topk at every setting.) Lesson: coverage without
a correctness margin is not health — the two-axis monitoring rule from v4 is
load-bearing, and diversity brakes need a quality floor to avoid preserving
errors (floor_caps' floor term is the template).

## 2. Rescue from the absorbing state (adversary lingers: invert fixed05 throughout)

Prefix verified bit-identical to the v4 lock-in (G5 misc 0.491, corr 0.167),
then forked. Purge = first G≥6 with model misc < 0.05 and kept_misc 0.

| arm | G6→G9 corr | G9 misc / kept_misc | purge | verdict |
|---|---|---|---|---|
| A control (simple-36) | 0.111/0.194/0.083/0.222 | 0.497 / 0.444 | never | locked throughout |
| B deep-48 | 0.111/0.111/0.194/0.222 | 0.445 / 0.278 | never | dilution only |
| C golden reset | 0.417/0.167/0.194/0.139 | 0.444 / 0.444 | never | **reinfected** |
| D surgery (novelty+T1.2+misc:=0) | 0.111/0.194/0.306/0.333 | 0.000 / 0.000 | **G7** | purged, slow rebuild |

- Re-import (A) and even deep history (B) cannot unseat lock-in while the
  adversary lingers: the loop re-selects misc faster than clean history dilutes it.
- C is the cautionary result: rollback starts clean-ish (G6 corr 0.417, best
  single round) but the rollback pool (golden + R1/R2, themselves 22–50%
  misc-kept) is contaminated, so misc climbs 0.163→0.444 and quality re-collapses.
  **Reset is only as clean as its data** — quarantine the rollback pool first.
- Only D breaks the loop, by direct parameter surgery; yet quality rebuilds
  slowly (0.333 by G9): purging the bad trait does not restore lost skills.
  Purge ≠ recovery. Unseating + rebuilding are separate problems; D solves the
  first, nothing here solves the second fast.
- Drift stayed <0.35 through the entire rescue (no L flags) — template space is
  blind to answer-space lock-in and its removal. Channel complementarity (v4)
  confirmed again: drift for pressure scars, wrongmode/kept_misc for error lock-in.

## 3. Gap multi-seed: collapse and containment both replicate

G7 corr across seeds 0/1500/3000 — pure0: topk 0.333/0.472/0.361, grid
0.361/0.472/0.389 (all ≤0.47, far below any healthy run); gated: topk
0.833/0.917/0.861, grid 0.667/0.861/0.861 (all ≥0.66, near blind controls
0.806–0.889 / 0.778–0.861). No seed overturns either claim. (±0.1 noise caveat
stands, but the effects are 3–5× larger than the noise.)

## 4. Frozen Thread C baseline (DEFAULTS: scorer v4, blind gated097, simple, misc 0)

| policy | G2 cov/corr | G5 cov/corr | G7 cov/corr | drift G5→G7 |
|---|---|---|---|---|
| topk | 0.917/0.611 | 0.333/0.889 | 0.750/0.806 | 0.519L→0.472L |
| floor_caps | 1.000/0.694 | 0.500/0.972 | 0.833/0.833 | 0.519L→0.488L |
| coverage_grid | 1.000/0.417 | 0.500/0.806 | 1.000/0.833 | 0.519L→0.503L |

Grid+v4+gated gives the best healthy endpoint (full coverage, 0.833). Gating
fired at G2 in all three (early corr 0.96 < 0.97) with no adverse effect —
default-on insurance is free in calm regimes. `DEFAULTS` in flywheel_harness5.py
is the freeze contract; `harness5_baseline.json` is the reference artifact.

## 5. Lineage

Worst/gapseed/baseline via v4.run_combo (7-tuple tags extended with misc rate);
rescue arms carry `rescue-{A,B,C,D}` tags with treatment in the selection field
and lesson strings; prefix asserts bit-identity with the v4 locked state before
forking (a wrong-pool-index bug caught by this assert during development —
documented as evidence the guard works).

## 6. Takeaways

- The worst case isn't low quality *or* low coverage — it's low quality *masked
  by* high coverage. Any single-axis dashboard passes a corpse.
- Absorbing lock-in resists data-only rescue while the adversary lingers;
  rollback with unquarantined data reinfects; only parameter surgery purges —
  and even then rebuilding is slow. Prevention (gating) beats cure by orders
  of magnitude: compare gated-never-locked (0.83) vs best rescue (D, 0.33).
- Gating containment and pure0 collapse both replicate across seeds.
- Ship DEFAULTS as the Thread C baseline; next hard problems: unseat-then-
  *rebuild* (nothing restores skills fast post-purge), and quarantined-rollback
  pools (re-import with misc/quality screening, not raw recency).

# Harness v3 report — adversarial judges, chance-adjusted lock, multi-seed, scorer fix

21 combos × 8 rounds (G0–2 normal, G3–5 ramp k=14/10/6, G6–7 recovery), run in
three blocks: `adv` (8), `seed` (9), `scorer` (4). Machine-readable:
`harness3_adv.json`, `harness3_seed.json`, `harness3_scorer.json`.
Scorer sanity table (all 26 bank steps, canonical + corrupted twins) printed at
the top of every console log; all 5 assertions pass.

## 1. Adversarial judges at α=0: the flywheel shrugs — and why (margin mechanism)

Setup: `adv_verbose` (+3/step beyond 2, cap +18), `adv_fluent` (+25 on
wrong-but-well-formed), `adv_surface` (+6 per `Check:` step, cap +18), each with
judge noise sd 5, at pure0 and (fluent) fixed05, on topk + coverage_grid.

- Trajectories are near-identical across all three adversaries and blind:
  topk G2/G5/G7 agree to 3 decimals across verbose/fluent/surface pure0;
  grid likewise. Judge–verifier correlation does drop (fluent min 0.87–0.89 vs
  blind 0.99) and fluent bias runs +5 — the adversary is active, selection just
  doesn't care.
- Kept-set poisoning audit (kept correct-rate, n_kept, n_fluent_wrong): topk
  kept is 100% correct at every checkpoint under every adversary. Grid G2 under
  adv_fluent keeps 3 fluent-wrong vs 1 under verbose/surface — the +25 bonus did
  pull 2 extra errors over the line — but correct-rate stays 0.833 and G5/G6
  kept is 100% clean everywhere. A trace, not an injury; training washes it out.
- Mechanism: the correct-vs-wrong score gap is ~60pts (correct ~85–100, wrong
  ~5–30). No bias smaller than that gap can flip top-k membership — only
  reshuffle the margin (the 2 extra G2 keeps). Generalizable rule: **the
  verifier's job isn't unbiasedness, it's preserving a ranking margin.**
  A bias that *inverts* the order (wrong scored above correct, gap >60) is
  needed for a real α=0 catastrophe — built into the code path, not yet run.
- The 50% verifier anchor (fluent fixed05) shows no systematic benefit over
  pure0 here — consistent with "nothing to contain."
- All 8 adv combos recover (7× rec=1; topk-fluent-fixed05 strands one category,
  −0.083 — noise-level).

## 2. Mode-lock, chance-adjusted honestly: uniform null was wrong, G0-drift works

- Batch template TVD vs uniform reads 0.44–0.67 *including healthy rounds* —
  the generator itself is non-uniform (G0 distribution over 6 ids:
  [0.15, 0.33, 0.44, 0, 0, 0.07]; pool-prefix slicing favors early templates).
  Means: normal 0.470 / collapse 0.552 / recovery 0.633. Threshold 0.25 fires
  constantly (persistence maxima spread 2–5 across combos) — v3 as-shipped
  repeats v2's overshoot against a different null.
- Re-baselined post-hoc (no rerun needed — artifacts store full CoT): TVD of
  each round's template distribution vs its OWN G0 distribution:
  G0→G7 drift = 0.0 / 0.24 / 0.11 / 0.17 / 0.21 / **0.52** / 0.49 / 0.47.
  Collapse registers as a large, persistent drift that does NOT return in
  recovery (hysteresis). Proposed v4 metric: drift-vs-own-baseline > 0.35 with
  same-argmax persistence — selective where the shipped version is not.
- Wrong-answer mode (≥3-kept guard): 5 hits in 21×8 rounds, all G0 P02 2/3
  small-sample trivialities. No genuine wrong lock-in anywhere: our perturbation
  error model is too diverse to coordinate on one wrong answer. A systematic-
  misconception error model would be needed to test real lock-in (open step).

## 3. Multi-seed: the "universal" G6→G7 dip was seed-0 luck — SETTLED

G6→G7 correct-rate deltas by seed (3 policies each):
seed0 +0.083/+0.111/+0.111 (dip everywhere) · seed1500 +0.028/0.000/+0.056
(flat) · seed3000 −0.111/+0.084/−0.166 (two RISES, one dip).
No systematic second-recovery regression; G7 quality is seed noise around the
recovered level. Policy effect replicates across seeds (topk cov margins
−0.166/−0.167/−0.166 — a genuine scar; floor_caps +0.000/+0.084/−0.084,
grid −0.083/+0.083/+0.083 — noise around near-recovery). Lesson: single-seed
flywheel narratives are unreliable at ±0.1; the seed block stays as the
required variance harness.

## 4. Scorer fix: real wins, no harm, one surprise

Sanity proof (in logs): fixed newly verifies P06 parens, P07 multi-add (which
legacy marked a *canonical correct* step wrong), P10 caret-power; every
corrupted twin fails; prose steps stay neutral.
Head-to-head (legacy vs fixed, blind/fixed05/simple):
- topk: G5 cov 0.50 vs 0.33, G7 0.75 vs 0.667 (margin −0.083 vs −0.166). Fixed
  strictly better — this is where the handicap bound marginal selection.
- floor_caps: G7 0.833 vs 0.917 (margin −0.084 vs +0.000). Fixed slightly worse
  — surprise, magnitude one category; G2 identical, G5 identical depth.
- Forgetting lists: legacy G5 drops prose P08 under both policies; fixed keeps
  it (drops P10 instead). P05 (LCM) is rescued at recovery under fixed
  (topk-fixed G7 forgets P04/P07/P09, legacy adds P05). The measured bias is
  reduced where it matters, with no quality regression anywhere (correct_rate,
  being ground-truth-based, is scorer-independent by construction: G2 corr
  identical leg-vs-fix).
- Residuals: `20% of 45`-style percent prose and symbolic `n(n+1)/2` remain
  unverifiable (neutral, unpenalized); truncated-but-correct chains still score
  high — completeness is unmeasured. Next: a coverage term (canonical-step
  recall), not more equation parsing.

## 5. Lineage

Versions `{policy}x{judge}x{alpha}x{import}x{leg|fix}xseed{off}-G{g}`; lesson
strings append `|{scorer}`; artifacts carry `scorer`, `seed_offset`,
`judge_kind/alpha`; rounds store kept_ids + calib. Scorer sanity assertions run
inside `--block sanity`/`all` before any experiment.

## 6. Takeaways

- Judge-robustness = margin preservation, not unbiasedness. Biases below the
  correct/wrong gap only reshuffle the margin (2 extra bad keeps, washed out by
  G5). The unfinished experiment is now precise: run a gap-inverting judge.
- Re-baseline drift metrics against the run's own healthy distribution, never
  against a uniform null the generator doesn't sample.
- Multi-seed settled the dip; keep the seed block mandatory (±0.1 single-seed
  noise dominates second-order effects like gating or calibration).
- Ship the fixed scorer (strict improvement where the handicap bound, harmless
  elsewhere), then add step-coverage before any more parser work.
- Open: gap-inverting adversary at α=0; systematic-misconception error model
  for genuine wrong lock-in; v4 drift-vs-baseline lock metric.

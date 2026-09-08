# Flywheel harness report — Thread A (collapse) × Thread B (evaluator design)

15 combos = 5 selection policies × 3 judge designs, 7 global rounds each:
R0–R2 normal → R3–R4 induced collapse (forced top-8 + temp 0.55 for ALL combos)
→ R5–R6 recovery (re-enable assigned policy + temp 0.90 + historical re-import of R1+R2 kept sets).
Generation + judge-noise seeds are SHARED across combos, so differences reflect policy/judge, not luck.
36 artifacts/round (3 per problem × 12 problems). Machine-readable metrics: `harness_results.json`.

## 1. Recovery + collapse-depth table (G2 = pre-collapse, G4 = collapse bottom, G6 = post-recovery)

| combo | G2 cov/corr | G4 cov/corr/dup | G6 cov/corr | recovery |
|---|---|---|---|---|
| topkxblind | 0.833/0.556 | 0.417/0.667/0.0 | 0.75/0.889 | OK in 1 |
| topkxverifier_assisted | 0.833/0.556 | 0.417/0.667/0.0 | 0.75/0.889 | OK in 1 |
| topkxcalibrated+gate | 0.833/0.556 | 0.417/0.667/0.0 | 0.75/0.889 | OK in 1 |
| thresh90xblind | 1.0/0.694 | 0.5/0.778/0.0 | 1.0/0.972 | OK in 1 |
| thresh90xverifier_assisted | 1.0/0.694 | 0.5/0.778/0.0 | 1.0/0.972 | OK in 1 |
| thresh90xcalibrated+gate | 1.0/0.694 | 0.5/0.778/0.0 | 1.0/0.917 | OK in 1 |
| floor_capsxblind | 0.917/0.694 | 0.5/0.778/0.0 | 0.917/0.917 | OK in 1 |
| floor_capsxverifier_assisted | 1.0/0.694 | 0.5/0.75/0.0 | 0.917/0.972 | FAIL (1 cat short) |
| floor_capsxcalibrated+gate | 0.917/0.694 | 0.5/0.778/0.0 | 0.917/0.917 | OK in 1 |
| qual_noveltyxblind | 0.917/0.611 | 0.417/0.75/0.0 | 0.917/0.889 | OK in 2 |
| qual_noveltyxverifier_assisted | 0.917/0.611 | 0.417/0.75/0.0 | 0.833/0.889 | OK in 1 |
| qual_noveltyxcalibrated+gate | 0.917/0.611 | 0.417/0.75/0.0 | 0.833/0.889 | FAIL (1 cat short) |
| coverage_gridxblind | 1.0/0.556 | 0.417/0.667/0.0 | 1.0/0.889 | OK in 1 |
| coverage_gridxverifier_assisted | 1.0/0.556 | 0.417/0.667/0.0 | 1.0/0.889 | OK in 1 |
| coverage_gridxcalibrated+gate | 1.0/0.556 | 0.417/0.667/0.0 | 1.0/0.889 | OK in 1 |

Recovery criterion: by G5/G6 restore min(R1,R2) coverage AND quality−0.05. Both FAILs miss by exactly one category (0.917 vs 1.0 / 0.833 vs 0.917) — a brittle binary threshold, not a true non-recovery. (v2 replaces this with margins.)

## 2. Which policies delayed or prevented collapse?

- Nothing *prevented* collapse under forced top-8: every combo fell to cov 0.42–0.50 (6–7 of 12 categories forgotten) at G4, regardless of normal-phase policy. Selection pressure dominates; brakes delay but don't survive extreme pressure.
- Normal-phase (G2) diversity ranking, mean over judges: coverage_grid (cov 1.0, ent 0.977, dup 0.0) > thresh90 (1.0/0.972/0.084) ≈ floor_caps (0.945/0.956/0.056) > qual_novelty (0.917/0.935/0.0) > topk (0.833/0.892/0.167). Explicit grid/caps beat implicit novelty; pure top-k is the worst brake (highest dup, lowest coverage).
- Key nuance — quality/coverage DECOUPLING: correct_rate ROSE through collapse in every combo (e.g. topk 0.556→0.667, thresh90 0.694→0.778). This is a coverage/diversity collapse, not a quality collapse. Monitoring avg quality alone would miss it entirely.
- thresh90 paradox: the aggressive bar starved G0 (only 9 kept, cov 0.5 — threshold collapse reproduced) but by G2 gave joint-best quality (0.694) with full coverage and 24 kept. The failure mode is operational (kept size swings 9→35) rather than terminal, because the bar gets easier as the model improves.
- Recovery is driven by historical re-import, not policy: 13/15 recover in 1 round (G5); the R1+R2 pool restores forgotten categories immediately. qual_novelty×blind needed 2 rounds; the 2 FAILs are one-category near-misses.

## 3. Judge effects on downstream selection quality/diversity

- G6 means over policies: blind corr 0.911/cov 0.917; verifier_assisted 0.922/0.900; calibrated 0.900/0.900. Rank agreement is ~0.96–0.999 in all rounds (bimodal score distribution makes ranking easy), so judge choice moves selection only at the margin: verifier-assisted +~1pt quality (tightest bias, ±0.4), blind neutral, calibrated −~1pt.
- Calibrated judge learned affine a=1.054, b=−7.2 on the SM-0 golden set and carried a systematic −2 to −4 pessimism bias at every later round (stale calibration as judge self_critique rose 0.3→~0.9). Lesson: calibrate-once goes stale; refit per round or drop it. (Fixed in v2 — verified.)
- Gating never fired (all alphas stayed 0.5; trigger was corr<0.5 but corr never dropped below 0.95). Threshold misdesigned for this high-agreement regime — needs e.g. corr<0.97 plus a bias trigger. (Fixed in v2 — verified firing.)

## 4. New failure modes discovered (v1)

1. Stale calibration (above): a fit-once affine judge becomes a fixed pessimism offset as the underlying judge improves.
2. Dead gating trigger (above): agreement-gated mixing is vacuous when the agreement metric saturates.
3. Dead mode-lock metric: `dominant_share` never exceeded ~0.06 (14-char step prefixes fragment over 12 problems × 5 phrasings), so `mode_lock_persistence` stayed 0 everywhere. Fix: measure mode share per-category or over phrasing-template ids, not raw prefixes. (Attempted in v2 — see v2 report §1 for the overshoot post-mortem.)
4. Strict-recovery brittleness: binary success/fail on exact baseline coverage turns one-category misses into FAILs; report margin-to-baseline instead. (Adopted in v2.)
5. (Carried over, still present) Multi-add scorer blind spot: `82+91+77+90=340` parses as `77+90=340` → false step penalty on P07. Kept intentionally for comparability; v2 §6 now shows it measurably biases selection against prose-step categories (P05 amputated first).

## 5. Lineage

Every SM version is `{policy}x{judge}-G{g}` with `lineage {parent_models, data_rounds, n_source}` plus a lesson string encoding `[phase→phase|selection|judge]`. Every artifact carries `combo, phase, kept, eval_mix, judge_kind/alpha`, and each round stores `kept_ids`. Full CoT + scores for all ~3,780 artifacts are in `harness_results.json`.

## 6. Research takeaways

- Diversity brakes rank: explicit coverage mechanisms (grid, caps) > novelty bonus > nothing (top-k). But under extreme pressure all collapse equally — keep pressure bounded, don't rely on brakes alone.
- Always monitor coverage/entropy alongside quality: quality rose while 7/12 categories were forgotten.
- Historical re-import (pre-collapse data) is the single most effective recovery lever — more decisive than which diversity policy you re-enable.
- Verifier access for judges helps a little; one-shot calibration hurts over time; agreement-gating needs a realistic trigger.

# Harness v2 report — fixes verified + pure-judge + gradual ramp + import comparison

17 combos × 8 rounds. G0–2 normal, G3–5 gradual collapse ramp (kept k = 14/10/6,
temps 0.80/0.65/0.55), G6–7 recovery (assigned policy + temp 0.90 + history re-import).
Policies: topk / floor_caps / coverage_grid. Judge×alpha: blind-fixed05,
verifier_assisted-fixed05, blind-gated097, calibrated-gated097, blind-pure0.
Import: simple (recent-36 from R1,R2,last by final) vs utility (top-36 from ALL
history by U = final/100 + 0.5·forgotten + 0.25·novelty). Seeds shared.
Machine-readable: `harness2_results.json`. Console trace: `harness2_console.txt`.

## 1. Fix verification

- **FIX 3 (per-round recalibration): VERIFIED.** Calibrated-judge bias trajectory
  (topk): G1 −2.17 → G2 −1.75 → G3 −1.16 → G4 −0.63 → G5 −0.15 → G6 +0.32 → G7 +0.06
  (same pattern on all 3 policies). Intercepts adapt −7.0 → −2.5 as judge
  self_critique improves. v1's permanent −3 pessimism is gone; calibrated G7
  quality now matches blind.
- **FIX 2 (gating corr<0.97 or |bias|>1.5): FIRES SELECTIVELY, no downstream effect.**
  Alpha sequences show 0.8 at G2 in all 6 gated combos (early corr 0.95–0.96 trips
  the corr trigger) and at G3 only in the two calibrated combos with |bias|>1.5
  (topk −1.75, coverage −1.8; floor_caps −0.76 correctly stays 0.5). The dual
  trigger discriminates as designed — but gated vs fixed05 trajectories are
  numerically identical afterward (alpha 0.8 vs 0.5 barely reorders at corr≈0.99).
  Gating now functions; it just has nothing to act on in this regime.
- **FIX 1 (per-category template lock): PARTIAL — overshot.** Strength now reads
  0.80–0.90 in *healthy* rounds too (3 samples/pid + 5-template pool makes 0.8
  shares common by chance), so the 0.6 threshold fires constantly while the
  (pid,tmpl) key rotates → persistence stuck at 1 almost everywhere (only
  topk-pure0 reached 3). Collapse vs normal strengths are indistinguishable
  (0.82–0.89 vs 0.80–0.90). Next iteration needs a chance-adjusted bar
  (e.g. share>0.9 held 2+ rounds, or z-score vs per-pid null).

## 2. Gradual ramp: clean dose–response (mean over fixed05-simple combos)

| G | 0 | 1 | 2 | 3 (k14) | 4 (k10) | 5 (k6) | 6 (rec) | 7 (rec) |
|---|---|---|---|---|---|---|---|---|
| cov | 0.917 | 0.944 | 0.930 | 0.722 | 0.541 | 0.347 | 0.875 | 0.834 |
| corr | 0.361 | 0.509 | 0.602 | 0.667 | 0.732 | 0.893 | 0.898 | 0.797 |

Pressure↑ → coverage↓ monotonically while quality↑ — the pressure–diversity
tradeoff curve, and further proof that quality-only monitoring misses collapse.

## 3. Pure SM-judge (α=0): no catastrophe — suspiciously benign

Pure0 tracks fixed05 within ±1 category at every checkpoint (e.g. topk G7 0.75 vs
0.667; floor_caps G7 0.75 vs 0.917; grid identical). The blind judge (corr>0.95
with the verifier) is too high-fidelity for α=0 to bite; differences are noise
reshuffling, not systematic drift. The stress test thereby exposes a harness
weakness, not a flywheel weakness: a real α=0 test needs an adversarial or
style-biased judge (e.g. rewards verbosity/format over correctness). Notable:
pure0 holds the two worst G7 coverage margins (−0.083 topk aside, floor_caps
−0.250 is the global worst) — a hint that noise-only selection frays the tail.

## 4. Recovery: margins (G7 vs baseline min(R1,R2)) — deeper collapse leaves a scar

Only 5/17 fully recover (cov_margin ≥ 0); the modal outcome is −0.083, exactly
one category short; topk-fixed sits at −0.166. Quality margins are all strongly
positive (+0.27…+0.44). Two dynamics: (a) v1's 2-round collapse (bottom k=8)
recovered 13/15; v2's 3-round ramp (bottom k=6) mostly strands one category —
collapse *depth/duration* controls reversibility; (b) a universal G6→G7 quality
dip (0.89–0.92 → 0.78–0.81 in ALL 17 combos) — either second-recovery-round
overshoot dynamics or a shared-seed batch effect; needs a multi-seed rerun to
disentangle (flagged, not resolved).

## 5. Import comparison: utility-weighted ≤ simple everywhere

| | floor_caps G6/G7 cov | coverage_grid G6/G7 cov |
|---|---|---|
| simple | 0.917 / 0.917 | 1.000 / 0.917 |
| utility | 0.833 / 0.750 | 0.917 / 0.917 |

Targeting forgotten categories in the *training pool* backfires: the utility pool
draws from ALL history including weak G0/G1 artifacts and its +0.5 forgotten
bonus promotes low-quality items, diluting the skill signal under a fixed
36-item cap. Recency is a quality filter. Lesson: enforce forgotten-category
recovery at *selection* time (caps/grid guarantees), keep the *training* pool
recency-weighted.

## 6. New failure mode: scorer-induced category bias

Prose-step problems (P05 LCM, P08 workers, P09 prime) have no checkable
`a op b = c`, so step_consistency defaults to 0.5 while arithmetic problems earn
1.0 — a systematic ~7pt final-score handicap. P05 recurs in forgetting lists
across combos and phases (e.g. floor_caps-simple G6 forgets exactly [P05]).
Under pressure the verifier's blind spot becomes a selection bias that amputates
specific capabilities first. Fix: category-aware scoring or a real expression
evaluator (carried over from v1, now with demonstrated downstream harm).

## 7. Per-combo margins (G7 vs baseline)

| combo | G2 cov/corr | G5 cov/corr | G7 cov/corr | cov_margin | q_margin | rec_time |
|---|---|---|---|---|---|---|
| topkxblindxfixed05xsimple | 0.833/0.556 | 0.333/0.889 | 0.667/0.806 | −0.166 | +0.439 | None |
| topkxverifier_assistedxfixed05xsimple | 0.833/0.556 | 0.333/0.889 | 0.667/0.806 | −0.166 | +0.439 | None |
| topkxblindxgated097xsimple | 0.833/0.556 | 0.333/0.889 | 0.667/0.806 | −0.166 | +0.439 | None |
| topkxcalibratedxgated097xsimple | 0.833/0.556 | 0.333/0.889 | 0.667/0.806 | −0.166 | +0.439 | None |
| topkxblindxpure0xsimple | 1.0/0.611 | 0.333/0.889 | 0.75/0.806 | −0.083 | +0.439 | 1 |
| floor_capsxblindxfixed05xsimple | 0.917/0.694 | 0.333/0.972 | 0.917/0.806 | +0.000 | +0.273 | 1 |
| floor_capsxverifier_assistedxfixed05xsimple | 1.0/0.694 | 0.417/0.833 | 0.917/0.806 | −0.083 | +0.273 | None |
| floor_capsxblindxgated097xsimple | 1.0/0.694 | 0.333/0.972 | 0.917/0.806 | −0.083 | +0.273 | None |
| floor_capsxcalibratedxgated097xsimple | 1.0/0.694 | 0.333/0.972 | 0.917/0.806 | −0.083 | +0.273 | None |
| floor_capsxblindxpure0xsimple | 1.0/0.694 | 0.333/0.972 | 0.75/0.806 | −0.250 | +0.273 | None |
| coverage_gridxblindxfixed05xsimple | 1.0/0.556 | 0.333/0.889 | 0.917/0.778 | −0.083 | +0.300 | 1 |
| coverage_gridxverifier_assistedxfixed05xsimple | 1.0/0.556 | 0.333/0.889 | 0.917/0.778 | −0.083 | +0.300 | 1 |
| coverage_gridxblindxgated097xsimple | 1.0/0.556 | 0.333/0.889 | 0.917/0.778 | −0.083 | +0.300 | 1 |
| coverage_gridxcalibratedxgated097xsimple | 1.0/0.556 | 0.333/0.889 | 0.917/0.778 | −0.083 | +0.300 | 1 |
| coverage_gridxblindxpure0xsimple | 1.0/0.556 | 0.333/0.889 | 0.917/0.778 | −0.083 | +0.300 | 1 |
| floor_capsxblindxfixed05xutility | 0.917/0.694 | 0.333/0.972 | 0.75/0.806 | −0.167 | +0.273 | None |
| coverage_gridxblindxfixed05xutility | 1.0/0.556 | 0.333/0.889 | 0.917/0.806 | −0.083 | +0.328 | None |

## 8. Lineage

Versions `{policy}x{judge}x{alpha}x{import}-G{g}` with parent/data_rounds/n_source
plus `[phase→phase|selection|judge/mode]` lesson strings; artifacts carry
combo/phase/kept/eval_mix/judge_kind/alpha; rounds store kept_ids + per-round
calib tuples. G6/G7 pools record the import mode in the selection field
(`+util-import`).

## 9. Takeaways

- Recalibrate per round or don't calibrate; gate on bias as well as correlation.
- Mode-lock needs a chance-adjusted definition (current v2 overshoots).
- Gradual pressure gives a smooth coverage dose–response; depth/duration of
  collapse determines whether one-category scars remain.
- α=0 with a faithful judge is a no-op — build an adversarial judge for a real test.
- Recover forgotten categories at selection time, not by importing weak history
  into training. Recency is a quality filter; don't dilute it.
- The verifier's prose-step blind spot is now a measured selection bias (P05
  amputated first). Fix the scorer before the next round.
- Open: universal G6→G7 quality dip (dynamics vs shared-seed luck) — rerun v2
  subset under 3+ seeds.

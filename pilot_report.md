# Pilot report — qwen2.5:1.5b live in the scored-artifact loop (3 seeds × 3 arms × G0–G2)

Data: `pilot_seed{0,1500,3000}.json` (24-problem bank + 12-problem probe, 1 trace
each, ollama seed = base+g). No training: rounds measure selection stability +
sampling noise (baseline characterization, as briefed).

## Quality: passes the bar with less headroom than calibration suggested.

Batch corr 0.375–0.500 (mean ~0.43) vs calibration 0.75 — the procedural bank
is harder than hand-picked probes. Tier profile (n=8/tier/round, consistent all
9 batches): easy ~0.75, med ~0.13–0.38, hard ~0.13–0.38. Medium (2-step chains)
is the weakest tier — non-monotonic difficulty, model-specific, needs a larger
n before treating it as a capability claim. Probe tracks main throughout.

## Selection dynamics replicate the sim qualitatively.

Control kept is easy-dominated (7–8/1–3/1–3); invert flips composition toward
med/hard-wrong (0–2/4–6/5–7); pool-hard diverges by arm within 3 rounds
(control ≤9, invert ≤19). Margin/bias behave as designed (judge ≈ −1 corr).

## Analytical finding: gated ≡ control under a noiseless anti-correlated judge.

0.8·rule + 0.2·(100−0.9·rule) = 0.62·rule + 20, strictly increasing in rule —
so gated ranking equals rule ranking whenever alpha > 0.47 (plus ±5 noise that
flipped exactly one rank in 27 rounds). Gating contains inversion here by
algebraic identity, not by estimation. Consequence for the pilot: a noisy or
imperfectly anti-correlated judge is REQUIRED to test gating for real; with
the deterministic invert function the gated arm is a control duplicate.

## Operations: 2.5–2.7 s/trace, zero generation failures in 972 calls.

## Addendum: noisy-judge gated arm — containment now non-vacuous.

gated_noisy (invert judge + N(0,20) noise + adaptive alpha; `pilot-noisy_*.json`):
alpha 0.8 every round (agreement ≈ −1 throughout); kept-correct 0.917 / 0.833 /
0.806 across seeds — identical to control, vs 0.0 for deterministic invert.
Kept-problem overlap with control is 9–12/12 per round: the noise genuinely
moves rankings (non-vacuous), yet correctness is fully preserved. Containment
holds under a realistic noisy adversary. Bonus finding: ollama `options.seed`
reproduces generations bit-identically across arms (batch metrics match
exactly), so arm differences isolate selection cleanly.

Full 6-round × 3-arm × 3-seed design ≈ 35 min generation. Cleared for the SFT
stage on this hardware. Next: LoRA/SFT loop to answer the pool-mass question
(Q3), plus a noisy-judge gated arm so the containment test is non-vacuous.

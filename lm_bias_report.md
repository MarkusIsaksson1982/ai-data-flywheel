# Biased-poison report — Gradients tolerate noise, not coordinated poisoning

3 runs (bias arm × 3 seeds; always-×2 corruption, invert selection+targets).
Data: `lm_bias.json`. Comparators in `lm_transfer.json` (G5 means over seeds).

## G5 test MSE by arm: easy / med / hard.

control 533 / 27k / 2.0M · invert 527 / 28k / 9.8M · gated 500 / 23k / 2.3M ·
**bias ~950 / ~460k / ~45M** — ~2× / ~17× / ~20× worse than control on every
slice, ~5× worse than invert on hard. Coordinated (non-zero-mean) poison
collapses performance GLOBALLY, including easy slices the unbiased arm spares:
shared weights propagate the bias everywhere. Clean pools sit at ~0 throughout
(vs ~80 control), so the bottleneck law has nothing to bite on — correctly, per
its scope condition (no correct mass ⇒ no learning; here the failure is active
misteaching, not missing mass).

## Verdict: the evaporation was about mean-preservation, not averaging per se.

Unbiased multiplicative noise (geometric mean ≈ 1) teaches the central tendency
and degrades hard-only ~5×; systematic ×2 bias (log-shift +0.30 that cannot
average out) breaks all slices 2–20×. Under gradient descent, the load-bearing
distinction is noise vs bias in the training targets — the sim-side margin rule
reappears in translated form: unbiased deviations are absorbed (same qualitative
role as below-gap proxies), systematic deviation compounds (same role as
gap-exceeding/inverting judges). Gating was not re-tested here (prior containment
result stands for the noise regime); the open follow-up is whether gated mixing
contains always-×2 (predict yes: 0.8 weight on true targets bounds bias to 20%).

## Confirmation: gating contains always-×2 (run after, `lm_gatedbias.json`).

gatedbias arm (invert judge + gated 0.8 mixing + ×2 corruption), 3 seeds:
agreement −0.995 fires alpha 0.8 every round; selected pools stay ~80+ clean per
slice (0.8·rule ranking sees through inversion); 20%-poisoned training targets
cause no measurable damage. G5 test MSE means — easy / med / hard: control
533/27k/2.0M · bias ~950/460k/45M · **gatedbias ~490/23k/2.1M**, i.e. containment
to control levels (≈20× better than the bias arm on hard). Disclosure of a
caught misrun: the first gatedbias attempt silently ran a faithful judge
(exact-string tuple membership missed the new arm name), producing a control
duplicate; caught on the agreement readout (+0.995 instead of −0.995), fixed
with a one-line tuple addition, rerun green. Containment now holds in both
regimes — unbiased noise (prior) and coordinated ×2 bias (here) — and the
gradient-harness transfer file is closed.

## Colab GPU follow-up: expert diet IMPROVES (opposite sign from local).

`tools/colab_expert_cell.py`, Qwen2.5-1.5B-Instruct + LoRA r=8 on T4 (bf16):
base-pre 13/30 → expert-post 17/30 (Δ+4), fixed-batch loss 1.398 → 0.471 over
27 steps (3 epochs). Local CPU runs showed 15→9 and 15→7 over 45 steps
(5 epochs) with loss driven to 0.21. Same data (identical 36 traces), same
recipe family — differing epochs (3 vs 5), dtype (bf16 vs fp32), hardware.
Leading hypothesis: overtraining — 45 steps memorize 36 traces (style capture
+ arithmetic disruption) while 27 steps partially learn. Discriminating test
(one-line change, rerun same cell): EPOCHS=5 on GPU. Degradation ⇒ overtraining
confirmed, prescription is early stopping; no degradation ⇒ dtype/hardware
regime effect (weaker mechanism, investigate second).

## GPU 5-epoch result: FLAT — overtraining hypothesis falsified, new suspect found.

Same cell, EPOCHS=5 (45 steps): base-pre 17/30 → expert-post 16/30 (Δ−1, noise),
fixed-batch loss 0.471 → 0.009 (full memorization, deeper than local's 0.21).
Overtraining does NOT reproduce the local degradation: memorization without
harm is possible. Remaining differences: bf16 vs fp32 (noise-as-regularizer
candidate), LoRA-init luck (n=1 GPU run at 5 epochs), and — most urgent —
BASE-EVAL INSTABILITY: GPU base-pre reads 13/30 then 17/30 across sessions with
identical weights/prompts/greedy decoding. If base eval jitters ±4, every diet
delta so far (local −6/−8 included) sits inside session noise. Required next
measurement before any diet claim: repeat base eval twice in one session, no
training. Stable (±1) ⇒ proceed to GPU repeats; jittery (±3+) ⇒ up probe N /
average repeats and re-bar all prior deltas.

## Colab GPU campaign table (machine-readable source: `refs/colab_gpu_results.json`).

| run | pool clean/36 | pre/30 | post/30 | Δ | loss | note |
|---|---|---|---|---|---|---|
| expert GPU#1 (3ep) | 36 | 13 | 17 | +4 | 1.40→0.47 | first GPU positive |
| expert GPU#2 (3ep) | 36 | 14 | 16 | +2 | — | repeat, same direction |
| expert GPU 5ep | 36 | 17 | 16 | −1 | 0.47→0.009 | memorization w/o harm; overtraining dead |
| clean 3ep | 36 | 14 | 16 | +2 | 1.352→0.436 | ≈ expert repeat (self-contained gen) |
| poisoned 3ep | 0 | 14 | 0 | −14 | 1.578→0.660 | floor collapse; correct-mass contrast decisive |
| poisoned repeat s1500 | 0 | 14 | 0 | −14 | — | CONFIRMED, not a fluke |
| mixed 18/18 | 18 | 14 | 0 | −14 | — | 50% poison still floors: damage asymmetric, non-linear, not proportional |
| stability | — | 14 | 14 | 0 | — | within-session noise ≈ 0 |
| local CPU ref | 33–36 | 15 | 9 / 7 | −6/−8 | →0.21 | recipe/hardware regime effect, unexplained |

Caveats (load-bearing): Grok-regenerated W/Z cells use different surface forms
than `tools/W_bank.json` / `tools/Z_probe.json` (answers mostly identical;
Z2-03 differs: 91 vs 528) — within-cell deltas valid, cross-cell absolutes not
strictly comparable. LoRA init fresh per session confounds cross-session
absolutes; within-session deltas controlled. Pending: poisoned repeat SEED=1500.

## 1.5B GPU sweep: FROZEN. Established: correct-mass pools help modestly
(+2 to +4); coordinated wrong-mass is catastrophic even at 50% (mixed 18/18
floors exactly like 100% poison) — damage is asymmetric and non-linear, not a
signal-noise average. Local CPU degradation is a different regime, not the
general story.

## Further verification (explicitly NOT immediate research).

These are recorded so the record stays honest about what remains unchecked;
none is needed for current claims:
- Light contamination (30 clean + 6 poison): is there a threshold, or does any
  systematic error floor? Optional by prior agreement.
- Second model family: cross-family confirmation before broader transfer claims.
- 5-epoch expert on a fresh session; LoRA-init variance quantification.
- Mixed-pool exact seed unrecorded: rerun with logged seed if bit-reproduction
  of the mixed cell is ever required.

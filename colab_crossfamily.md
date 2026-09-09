# Colab cross-family SFT: expert diet gains on SmolLM2 + TinyLlama (Qwen dissociates)

## Runs (single-cell GPU, T4, recipe parity except noted)
- `tools/colab_singlecell_smollm2.py` (HuggingFaceTB/SmolLM2-1.7B-Instruct):
  pre **12/30** → post **16/30** (+4), fixed loss 1.180 → 0.374, 27 steps / 8 s. CELL DONE.
- `tools/colab_singlecell_tinyllama.py` (TinyLlama-1.1B-Chat-v1.0):
  pre **1/30** → post **8/30** (+7), fixed loss 1.482 → 0.289, 27 steps / 5 s. CELL DONE.
- Qwen reference (local CPU, `sft_seed{0,1500,3000}_expert.json`): 15→9, 15→7, 14→13.

## Verdict: expert-diet evaporation is NOT family-universal
Two non-Qwen families GAIN under the same expert diet that drops Qwen. The SFT-track
"evaporation" does not generalize as a diet property. But the dissociation is
CONFOUNDED three ways — no family claim is licensed yet:
1. **Dose**: Qwen ran EPOCHS=5; Colab cells run EPOCHS=3 (Qwen's drop may be overtraining).
2. **Baseline/headroom**: pre = 15 (Qwen) / 12 (SmolLM2) / 1 (TinyLlama). TinyLlama's +7
   starts at floor — format-learning ("Final: <n>") may dominate capability gain.
3. **Device/dtype**: Qwen fp32 CPU vs new runs fp16 T4 (no Qwen GPU result on record).

## Next rung (dose-match, same loop, one-digit edits)
- (a) Re-run both cells with EPOCHS=5 (match Qwen dose): if gains hold → family/baseline
  story; if they drop → dose story, Qwen "evaporation" was overtraining. RECOMMENDED first.
- (b) Seeds 1500/3000 at 3 epochs (pool variation; Qwen has 3 seeds). Edit SEED constant.
- (c) Qwen GPU cell at 3 epochs (match new dose from the other side).
- Instrumentation gap: cells return aggregates only — per-tier/format-vs-arithmetic split
  needed to separate format-learning (TinyLlama floor) from reasoning gain. Queued.

## Loop status
Feedback loop confirmed: paste-output → diagnose → push fix → re-run, two cycles
(torchao≥0.16 fix `fcbfc52`, clean runs after). torchao .so warnings (mxfp8/cutlass,
cp310 vs py3.13) are cosmetic — LoRA trained fine.

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

## Dose-match (5 epochs): dose story DEAD
- SmolLM2 5ep: pre **12/30** → post **17/30** (+5; was +4 at 3ep), loss 1.180 → 0.046.
- TinyLlama 5ep: pre **1/30** → post **12/30** (+11; was +7 at 3ep), loss 1.482 → 0.030.
- Near-memorization losses (0.03–0.05) yet probe GAINS — memorization did not hurt
  generalization here. Qwen's 5-epoch drop (15→9/7, 14→13) is not dose: same dose
  improves both other models. Remaining confounds: baseline/headroom (15/12/1) and
  device/dtype (Qwen fp32 CPU vs fp16 T4). Next: Qwen GPU cell at 3 epochs (same loop)
  to close   device/dtype; then seeds 1500/3000 for the new models.

## Qwen on GPU: evaporation does NOT reproduce — artifact retired
- Qwen GPU 3ep (`tools/colab_singlecell_qwen.py`): pre **14/30** → post **15/30** (+1),
  loss 1.400 → 0.428. Holds.
- Qwen GPU 5ep: pre **14/30** → post **19/30** (+5), loss → 0.069. Best result yet.
- Qwen CPU fp32 5ep (old local ref): 15→9, 15→7, 14→13. The collapse is specific to
  the old CPU/fp32 stack — not family, not dose, not baseline. The SFT-track
  "evaporation" finding is RETIRED as a diet/family property (kept as: LoRA-SFT on
  CPU-fp32 with this recipe can destroy where GPU-fp16 builds — stack-sensitivity note).
- Cross-family confirmation ACHIEVED: all three families gain on GPU at both doses,
  monotonically with dose (3ep → 5ep: Qwen +1→+5, SmolLM2 +4→+5, TinyLlama +7→+11).

## Next rung (dose closed; baseline + device remain)
- (a) DONE — dose eliminated (this section above).
- (b) Batched seeds 1500+3000 + per-tier/format instrumentation, ONE run per model at
  EPOCHS=5 (all models gain more at 5; model reloaded fresh per seed, no adapter
  compounding): `tools/colab_batch_{qwen,smollm2,tinyllama}.py`. Splits TinyLlama
  format-learning from reasoning gain (probe is 10/10/10 per tier).
- (c) Qwen GPU single-cell at 3 epochs (dose+device match from the Qwen side) — cell
  `tools/colab_singlecell_qwen.py` emitted alongside the others.
- Instrumentation gap: cells return aggregates only — per-tier/format-vs-arithmetic split
  needed to separate format-learning (TinyLlama floor) from reasoning gain. Queued.

## Loop status
Feedback loop confirmed: paste-output → diagnose → push fix → re-run, two cycles
(torchao≥0.16 fix `fcbfc52`, clean runs after). torchao .so warnings (mxfp8/cutlass,
cp310 vs py3.13) are cosmetic — LoRA trained fine.

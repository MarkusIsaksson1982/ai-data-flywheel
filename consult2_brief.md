# CONSULT-2 brief — hard-dose SFT vs t2 immobility (RAISED 2026-09-10, GPU approved)

## Question
Does sustained HARD dose move t2 (hard probe) where 36-trace mixed expert diet could
not? (Cross-family: t2 = 0/10 pre AND post in all 6 prior GPU runs; easy/med move.)

## Transfer theory (stated to survive external reading — deepseek constraint)
In-sim, depth's probe effect is conditional on tier skill ~0.99; at terminal skill
~0.85 (pkg29 AND pkg30) depth moves probe within noise; intermediate range untested.
Correction: pkg30 (base 0.45 → terminal 0.834) was NOT a low-skill test — it is a
second sample at ~0.85 next to pkg29's 0.864. The interaction is observed between two
saturation clusters (~0.85 vs ~0.99), not along a gradient. Whether real LoRA SFT on
a skill-saturated slice exhibits an analogous depth lever — and how "saturated" maps
to real-model competence — is THIS SFT's test. The sim cannot license it; it motivates it.

## Design honesty (what is and isn't isolated)
The bank confounds length≡tier (t0:1 step, t1:2, t2:3–4; only 8 hard problems). So:
- Arm A (control): 36-trace mixed expert diet (replication anchor for prior runs).
- Arm B (test): 36 HARD traces (3–4 steps) — mass+length+difficulty BUNDLED, labeled
  as bundled. Answers "does sustained hard dose move t2", NOT "does length matter".
- Length-at-matched-difficulty requires new bank problems (short-hard, long-easy) —
  explicitly out of scope; queued follow-up, needs frozen-data extension.
- Epochs chained in-run: train 3ep → eval → continue to 5ep → eval (same adapter).
- Seeds [0, 1500, 3000] batched; per-tier + fmt instrumentation (proven template);
  fresh reload per (seed, arm); 3 per-model cells (user runs parallel sessions).

## Pre-registered outcomes
- Null (legitimate, pushable): t2 stays 0/10 in BOTH arms (skill-absence deeper than
  dose; sim's ≤2-arts rule does not transfer).
- Positive: t2 moves in B on ≥2/3 families (dose moves what mixed diet couldn't).
- Split: moves on one family only → family×dose interaction, new rung.
- Watch: fmt collapse masking accuracy (TinyLlama precedent — report fmt always).

## GPU budget
3 models (Qwen/SmolLM2/TinyLlama) × 3 seeds × 2 arms × (3ep+2ep chained) ≈ 30 min
per per-model cell on T4/fp16. No run-count limits; bottleneck is paste labor —
hence 3 cells. Crash loses one cell max (seeds sequential, adapters reloaded).

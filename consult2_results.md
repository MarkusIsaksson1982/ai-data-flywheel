# CONSULT-2 results — hard dose does not move t2 (null confirmed, transfer gap found)

## Runs (`tools/colab_harddose_*.py`: seeds [0,1500,3000] × {mixed, hard} × 3ep→5ep)
- Qwen post-5ep: mixed 17/19/16, hard 18/18/18. t2 = 0/10 everywhere, all epochs.
- SmolLM2 post-5ep: mixed 14/15/16, hard 14/17/16. t2 = 0/10 everywhere.
- TinyLlama post-5ep: mixed 9/6/4, hard 4/3/2. t2 = 0/10 everywhere.
- Losses fall in all 18 runs (0.03–0.12): learning happened; hard probe didn't move.

## Verdict: pre-registered NULL (legitimate, pushable) — scoped precisely
t2 stays 0/10 in BOTH arms on all families. Sustained bundled hard dose (36 hard
traces × 5ep) cannot create t2 skill from a 0/10 base. Scope discipline (round7):
- The sim NEVER tested creation from zero (pkg29 base 0.55, degraded not absent):
  the ≤2-arts rule describes sustaining/recovering partially-possessed skill against
  forgetting — a different regime from creation. The sim rule also applied to hard
  mass embedded in MIXED pools; the hard arm is hard-only. So "transfer gap" is right,
  but the reason is overdetermined: different substrate (scalar heuristic vs gradient
  descent), different regime (maintenance vs creation), different input (mixed vs
  hard-only). Expecting transfer was the error, not the null.
- The axis, not the amount, fails: tier_acc has no real-model analogue; capability on
  hard probes comes from pretraining, not SFT dose. 36 hard traces can't create the
  pattern — and neither, on this reading, could 100 or 300 of the same axis.
- Floor-effect honesty: at n=10, "0 stays 0" means NO BIG JUMP, not "no effect"
  (1–2 newly-correct items would barely register). A harder base (t2 2–4/10) or n≥30
  probe would be needed to strengthen this null. It stands as a bound, not a zero.
- What DOES transfer: the interaction structure (depth inert below saturation —
  confirmed real-weights), while the acquisition threshold does not. Sim dynamics
  partially transfer; sim thresholds don't.
- Candidate explanations for the gap (hypotheses, NOT findings): pre-training gap;
  LoRA capacity (r=8 ≈ 1M params; multi-step reasoning may need coordinated
  cross-layer change — discriminator: full-finetune or larger rank on the same 36
  traces); skill×depth interaction. Queued, untested.

## Secondary findings (all pre-registered watch-items)
1. **Non-monotonic epoch trajectories**: Qwen s1500 mixed 14→12→19; SmolLM2 s0 mixed
   17→14 (reversal DOWN 3ep→5ep). Chained evals are now DEFAULT methodology, not a
   nice-to-have: single-point reads miss or overstate by ~3/30 either direction.
   Retroactive caveat (explicit): ALL prior GPU numbers (`colab_crossfamily.md`,
   `sft_*.json`, single/batch cells) are single-endpoint reads — they stand as
   measured but their trajectories are unknown, and any 3ep-only comparison is suspect.
2. **Hard-only diet starves floor models — LED here, not footnote**: TinyLlama fmt
   12→2 (s3000, 3ep→5ep) is a stronger effect than the accuracy moves attached to it.
   Mechanism read: hard-only diet withholds the easy traces that anchor format while
   supplying signal the floor model cannot use (diet-design error; predicts even
   minimal easy/med scaffolding prevents it — testable). At n=30, format is the metric
   that actually moves; accuracy sits near noise. "Training worked" (loss fell) is
   partly a format story everywhere at this N.
3. **Format/accuracy dissociation (Qwen)**: fmt 30→~21 while accuracy rises 14→18 —
   second sim boundary condition (sim's format_rel/arithmetic_acc update independently;
   real weights entangle them; LoRA optimizes reasoning patterns at formatting's
   expense). No format-vs-reasoning tradeoff exists in the sim; record the absence.
4. Hard arm never beats mixed on t2 (both zero). On harm: at n=30 with ±2–3 noise,
   "hard never beats mixed" is CONSISTENT WITH NULL, not evidence of harm — except
   the TinyLlama s3000 fmt collapse, called out above. No directional harm claim.

## Status
CONSULT-2 CLOSED with null. Length-isolation (bank extension) stays queued but
demoted: with t2 immobile under any dose tried, isolating length answers a question
behind the binding constraint (skill presence). Next SFT question belongs to
skill-creation (pre-training gap?), not dose-formulation — external round material.

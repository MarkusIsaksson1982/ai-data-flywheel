# CONSULT-2 results — hard dose does not move t2 (null confirmed, transfer gap found)

## Runs (`tools/colab_harddose_*.py`: seeds [0,1500,3000] × {mixed, hard} × 3ep→5ep)
- Qwen post-5ep: mixed 17/19/16, hard 18/18/18. t2 = 0/10 everywhere, all epochs.
- SmolLM2 post-5ep: mixed 14/15/16, hard 14/17/16. t2 = 0/10 everywhere.
- TinyLlama post-5ep: mixed 9/6/4, hard 4/3/2. t2 = 0/10 everywhere.
- Losses fall in all 18 runs (0.03–0.12): learning happened; hard probe didn't move.

## Verdict: pre-registered NULL (legitimate, pushable)
t2 stays 0/10 in BOTH arms on all families. Sustained bundled hard dose (36 hard
traces × 5ep) cannot create t2 skill from a 0/10 base. The sim's ≤2-arts
presence rule does NOT transfer to real LoRA SFT — the transfer theory's weak link,
identified empirically rather than assumed. Sim→real DIVERGENCE, foreground it:
in-sim presence suffices; real-model hard skill needs something dose alone (as
constructed here) doesn't supply — pre-training gap vs dose-formulation stays open,
no claim beyond the null.

## Secondary findings (all pre-registered watch-items)
1. **Non-monotonic epoch trajectories**: Qwen s1500 mixed 14→12→19; SmolLM2 s0 mixed
   17→14 (reversal DOWN 3ep→5ep). Single-epoch reads mislead either direction —
   chained evals justified; any 3ep-only claim from prior cells is now suspect
   (prior 3ep numbers stand as measured, but their trajectories are unknown).
2. **Hard-only diet starves floor models**: TinyLlama mixed 9/6/4 beats hard 4/3/2;
   hard-arm fmt collapses (s3000: 12→2 from 3ep→5ep). Easy traces teach format;
   hard-only diet on a floor model degrades it. Diet composition > diet difficulty.
3. **Format/accuracy dissociation (Qwen)**: fmt 30→~21 from 3ep→5ep while accuracy
   rises 14→18. Another train-vs-held-out-style dissociation for the ledger: format
   compliance is not capability, in either direction.
4. Hard arm never beats mixed on t2 (both zero) AND never beats mixed overall
   except Qwen s0/s3000 ties (+1/+2, inside noise): no evidence hard-heavy helps
   anything measured here; weak evidence it hurts floor models.

## Status
CONSULT-2 CLOSED with null. Length-isolation (bank extension) stays queued but
demoted: with t2 immobile under any dose tried, isolating length answers a question
behind the binding constraint (skill presence). Next SFT question belongs to
skill-creation (pre-training gap?), not dose-formulation — external round material.

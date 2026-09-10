# CONSULT-2 follow-ups — rank-sweep null, scaffold weak, collapse not replicated

## Rank-sweep (Qwen, hard arm, r8 vs r32; `tools/colab_ranksweep_qwen.py`)
Post-5ep: r8 19/20/17 vs r32 17/18/19 (deltas −2/−2/+2, mean 0). t2 = 0/10 all 6 runs.
r32 losses lower (0.028–0.054 vs 0.057–0.107: 4× params memorize better) with
identical probes — capacity buys memorization, not skill. **Adapter capacity NOT
binding** at this dose/scale (r ≤ 32). Pre-training-gap hypothesis survives;
full-finetune escalation DEMOTED (unlikely to differ at this dose without new motive).

## Scaffold-rescue (TinyLlama, hard-only vs 30hard+6easy; `tools/colab_scaffold_tinyllama.py`)
Post-5ep acc: hard-only 4/8/4 vs scaffold 6/4/6 (net 0). fmt: scaffold holds better
(+5/+5/+1: 20/20/14 vs 15/15/13) but **the s3000 12→2 collapse did NOT replicate**
(hard-only s3000 fmt 12→13 here). Verdict: diet-composition accuracy effect unproven;
prior collapse was single-run fluctuation, downgraded. Standing finding instead: fmt
volatility itself (±10 at n=30) — the metric is too noisy to carry claims, which cuts
both ways (no collapse claim AND no rescue claim beyond "holds modestly better").

## SFT track status
Closed pending new ideas. Open questions and their state:
- Skill creation from zero: null everywhere tried (dose, rank, scaffold). Remaining
  motives (full-FT, bigger models, curriculum, more dose) are all expensive with no
  positive lead — parked, not queued.
- Length-isolation: still demoted behind bank extension (t2 has no symptom for length).
- Bank extension (short-hard/long-easy frozen data): the one unbuilt dependency; no
  motive until a skill-present slice exists to test depth on.
Next SFT work only on external-round findings or prompter direction. Sim queue
(router integration WQ2b-gated, matched-pool sidecar) unaffected.

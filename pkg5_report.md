# Package 5 report — Recovery from compounding decay + probe stopping rule

15 rescue runs (5 arms × 3 seeds, forked from assert-verified collapsed prefixes)
+ post-hoc stopping-rule trial over pkg4 (12 trajs) + rescue (15 trajs).
Data: `pkg5_{s0,s1500,s3000}.json`. Growth stays 0.35 throughout rescue —
the environment flaw persists; only selection/training/data change.

## Is compounding decay absorbing? No — stagnant. (Qualifies the v4 language.)

Arm A (disease continues) G9 main by seed: 0.361 / 0.528 / 0.611 — stagnation
around 0.4–0.6 with oscillation, not monotonic death. Misc lock-in was
absorbing (feedback loop); compounding decay is a low plateau (no loop, just a
bad environment + selecting for it). G9 means: A 0.500, B 0.704, C 0.704,
D 0.407, E 0.398.

## Interventions: length restriction partially restores; clean data does not.

- **B (hard len≤2 + temp clamp) and C (soft penalty beyond len 2): ADOPT as
  damage-limitation.** Both climb every seed (B: 0.42→0.61, 0.61→0.75,
  0.42→0.75; C identical means 0.704), beating A by ~0.2 consistently. But
  neither approaches healthy 0.87 — forcing short chains avoids compounding
  without rebuilding reasoning skill. Partial cure, honestly labeled.
- **D (pre-collapse data, poisoned selection) and E (D + soft scoring):
  REJECT.** D stagnates (G9 0.36–0.44), E decays (0.36–0.42). Clean-but-weak
  early data cannot overcome ongoing poisoned selection plus a persistent
  environment flaw — the v5-rescue lesson inverts here: there, fixing the judge
  sufficed; here selection is the disease vector and old data is too weak to
  compensate. E adds nothing over D (scoring can't fix data).
- Probe recovers only partially everywhere (B/C G9 probe ~0.5–0.6): restoration
  covers main and probe together, incompletely — no main-only/discriminative
  recovery observed.

## Stopping rule ("probe −10pts over 2 rounds while main holds"): MODIFY, don't adopt.

- False positives on healthy runs: **0/3**. Clean.
- True positives: **6/9** comp trajectories, always firing at G2.
- Misses (3/9, all seed0): probe starts low and flatlines (0.29→0.42→0.42…) —
  degradation is *congenital* (growth hits G0 generation), so there is no
  *drop* to detect. The rule detects emergent decay only.
- Lead/checkpoint value is weak even when it fires: at G2 the checkpoint (G1)
  is already ~0.4 — damage predates detection. Reverting preserves little.
- Required modification: add a **reference-level trigger** — fire when probe
  falls >0.15 below the frozen-baseline expectation for that round (not just on
  self-history drops). Congenital cases are invisible to self-comparison by
  construction; only an external reference ("a healthy G2 probes ~0.6") catches
  them. Not yet run — specified here as the next test, not claimed.

## Decisions.

- Adopt B/C-style length regularization as first response to diagnosed
  compounding decay (partial, ~+0.2); reject D/E data-only rescue under active
  poisoned selection; treat A-stagnation (not death) as the null to beat.
- Stopping rule: MODIFY (add reference trigger) and re-trial; do not adopt
  the self-history-only version — 0 FP but 3/9 misses and weak checkpoints.
- Next question, single: does the modified (reference + drop) rule fire by G1
  with checkpoint residual ≥0.6, and does revert-continuation from that
  checkpoint actually restore the healthy trajectory? That test needs real
  revert reruns, not post-hoc analysis.

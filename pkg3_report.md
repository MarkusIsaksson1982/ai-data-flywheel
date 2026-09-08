# Package 3 report — Breaking the margin rule: attempted, recalibrated, bounded

21 combos (7 arms × 3 seeds, 6 normal rounds). Data: `pkg3_{base,trap,break}.json`.
Complexity increase vs settled baseline: (1) generator with a genuine
fluency↔correctness tradeoff (trap_rate — rambling derails the final answer,
format stays well-formed; verified: 15/16 trapped arts wrong-yet-fluent);
(2) heritable verbosity (next temp tracks kept length — compounding loop);
(3) proxy weights spanning the margin (+12/+30/+80 per step).

## Dose–response at G5 (main-corr means over seeds; probe in brackets).

| arm | w | trap | main | probe | keptlen |
|---|---|---|---|---|---|
| control | — | 0 | 0.870 | 0.875 | ~2.0 |
| gap12 | 12 | 0 | 0.907 | 0.890 | ~2.2 |
| gap30 | 30 | 0 | 0.907 | 0.875 | ~2.2 |
| trap30 | 30 | .6 | 0.769 | 0.847 | ~2.1 |
| guard30 | 30+nov/cap | .6 | 0.880 | 0.850 | ~1.7 |
| gap80 | 80 | 0 | 0.815 | 0.750 | ~2.4 |
| guard80 | 80+nov/cap | .6 | 0.778 | 0.695 | ~2.0 |

gap12 ≡ gap30 bit-identically (all seeds, all rounds): with in-pool length
differentials ≤2, no correct/wrong pair straddles the +12 vs +30 flip boundary —
the bimodal score structure makes the two weights rank-identically.

## The +30 calibration was wrong; +80 gives a bounded effect, not a break.

Flip condition for correct-short (rule ~95) vs wrong-long (rule ~15): needs
w·Δlen > 80, i.e. Δlen ≥ 3 at w=30. The generator cannot supply it (chains cap
at ~4 steps; distractors ~8%), so +30 could never flip — miscalibrated test,
honestly reported. At +80 (one extra step outweighs the whole gap) selection
does shift (keptlen 2.4, longest-first) — yet quality costs only ~0.06–0.09 and
nothing collapses. Reason: within length strata the gap reasserts itself
(4-step correct ≈ 415 ≫ trapped-wrong ≈ 255). **Refined rule: exceeding the gap
is necessary but not sufficient — the proxy trait must ANTI-correlate with
correctness at scale (invert judge, misconception feedback), not merely be
orthogonal to it (length).** Length can never do that here because long chains
are built from the same low-corruption process as short ones. The trap (wrong
5% of arts) + heritable temp (saturated ~1.0, starved by the length ceiling)
never concentrated wrongness at the top. Breaking quality via verbosity would
require a generator where verbosity itself causes wrongness at scale.

## Guardrail + tripwire record.

Cap binds (guard keptlen ≤2.0 vs 2.4 unguarded) at zero capability cost
(guard30 0.880 ≈ control; guard80 tracks gap80-minus-trap). Drift never locked
(max 0.21 — correct silence, no collapse to mark); gating fired occasional
early 0.8s on blind noise (harmless); probe gaps stayed <0.2 (largest: gap80
seed0 G5 +0.18, noise-level). Tripwires behaved: silence where nothing failed.

## Decisions.

- REJECT heritable temperature as a default mechanism (saturates, adds nothing).
- KEEP trap_rate in the generator (default 0) as the approved way to model
  fluency–correctness tradeoffs in future work.
- KEEP length-bin cap as hygiene (binds, free). No change to frozen scoring/
  judge/import defaults — nothing here measured a reason to override them.
- Highest-value next question: a generator in which the rewarded trait and
  wrongness coincide structurally (e.g. a learned verbosity policy, or long
  chains that compound error multiplicatively) — or accept margin-structural
  robustness as this platform's scope boundary and move up in realism instead.

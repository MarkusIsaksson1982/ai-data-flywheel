# Workqueue — contribution-typed flywheel (living document)

Source: synthesis of 7 external analyses (`reference-content/2026-09-10`), translated to
generic tiers (Frontier/Mid/Cheap/Human/External/Verifier/Environment).
Rule: this file is updated — items reordered, rescoped, or parked — whenever an item's
results change what the next item should be. Conditions below are binding, not advisory.

## State (2026-09-10, P1 pushed)
- WQ1 DONE/PASS (84/84, zero recombine; `tools/contrib_taxonomy.py`, `wq1_contrib.md`).
  Condition B not triggered. WQ2/WQ4/WQ5 unlocked.
- WQ2 DONE/PASS on EV (+0.046/cell, 10/15 directional; s3000 washout documented;
  `tools/fitness_gate.py`, `wq2_fitness.md`). Router integration into
  `harvest_path_for` QUEUED (canonical routing untouched deliberately).
- WQ6 DONE (additive `stack` param + `stack_assumed` stamp; tests 30/30).
- NEXT: WQ3 design, then CONSULT-1 (tier roles) before WQ4 runs.

## Tier legend
Frontier = flagship reasoning tier · Mid = balanced tier · Cheap = high-volume sampler
tier · Human/External/Verifier/Environment = non-model sources.

## Items

### WQ1 — Contribution-type taxonomy instrument (SIM, zero new runs) [DONE/PASS]
Score every generation/branch per slice as one of:
preserve / amplify / discover / recombine / drift / dormant / degrade,
plus an evaluator-improve axis (judge_corr/agreement vs parent).
Thresholds: EPS=0.02 preserve band, DELTA=0.05 amplify, FLOOR=0.35 absent, HIGH=0.60 present.
Validate by classifying existing runs with KNOWN answers:
- pkg24 E-branch → amplify t0/t1; W-branch → degrade; scalar-merged → degrade-via-parent.
- pkg21 E/H branches → amplify own tiers; merged arm → preserve at best (consult null:
  NO recombine expected — a recombine hit here falsifies the consult verdict, handle as P0).
- pkg26 polluted G4 → degrade; pruned → preserve/amplify (== single).
- PASS BAR: ≥80% of known-answer cells classify as predicted, zero recombine hits on
  pkg21-merged. Output: `tools/contrib_taxonomy.py` + `wq1_contrib.md`.
- CONDITION A: pass → unlocks WQ2, WQ4, WQ5 (all consume the taxonomy).
- CONDITION B: recombine hit on pkg21-merged → STOP the queue, re-open consult verdict
  (P0 incident); nothing else runs until resolved.

### WQ2 — Parent-fitness gate for the harvest router (SIM, zero new runs)
Flag weight lineages carrying unresolved veto/quality issues; gate any
`bank-regenerate-or-adapter` path on fitness, separately from data importability.
Validate on pkg24/26: merged & polluted lineages must flag; single/pruned must not.
Output: fitness function (in/near `capability_ledger.py` harvest path) + `wq2_fitness.md`.
- CONDITION: fitness never triggers on any existing lineage → PARK (no discrimination,
  revisit only with new regimes); else proceed to P1 push.

### WQ6 — Stack provenance in ledger entries (TRIVIAL, fast)
Add device/dtype (+ dose, epochs) to ledger provenance metadata wherever entries are
built; backfill stamps as `assumed` where unknown (same discipline as `n_assumed`).
No experiment. Joins P1 push.

### WQ3 — Judge-margin tripwire (DESIGN → SIM)
The open instrument: measure the judge's ranking-margin lead over the generator, with a
tripwire when the margin thins (gaming regime). Needs WQ1's evaluator-improve axis.
Design first, simulate second (invert-strength sweep reusing harness4 judges).
- CONDITION: if WQ1 evaluator axis shows no measurable movement in any existing run
  (judge_corr flat everywhere) → design-only, no sim (nothing to calibrate against).

### WQ4 — Heterogeneous-ecosystem sim test (SIM RUNS, expensive)
Cheap-breadth + Mid-filter + Frontier-critique tiers with distinct roles vs single-tier
loop; endpoint = WQ1-measured recombination (jointly-accessible capability no single
tier sustains). Needs WQ1 (recombine metric) + prompter nod on tier roles (CONSULT-1).
- CONDITION: if WQ1 recombine class proves unmeasurable even on pkg21-style agreement
  cases → descope to design-only.
- CONDITION: result "no recombination" → still P2-pushable (null of record), but WQ5-SFT
  loses its recombination motive; proceed on dose×tier motive only.

### WQ5 — Dose×tier mapping (SIM → SFT)
Sim first: vary pool correct-mass per tier × dose, map dose thresholds per tier (does
hard need mass, duration, or both?). SFT long-dose (100+ traces) ONLY if sim shows a
reachable threshold AND prompter approves Colab time (CONSULT-2).
- CONDITION: sim dose×tier flat (no threshold in range) → SKIP SFT long-dose entirely.

## Plateaus & push gates (minor progress is NOT pushed)
- **P1 — Instruments plateau**: WQ1 + WQ2 (+WQ6). Push when all three land or park with
  written verdicts. → CONSULT-0 (external analyses) on push.
- **P2 — Ecosystem plateau**: WQ3 + WQ4 (+WQ5-sim). Push when done/parked. → CONSULT-0.
- **P3 — Real-weights plateau**: WQ5-SFT iff greenlit. Push on completion. → CONSULT-0.

## Prompter consult points (raised in TUI output, never auto-passed)
- CONSULT-0: after every plateau push — external-model analyses invited.
- CONSULT-1: before WQ4 runs — tier roles & cost model for the heterogeneous design.
- CONSULT-2: before any SFT long-dose — Colab time/dose approval.
- Plus: any CONDITION-B/P0 incident, and any proposal to spend Colab/GPU time, is raised
  immediately regardless of plateau position.

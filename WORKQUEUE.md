# Workqueue — contribution-typed flywheel (living document)

Source: synthesis of 7 external analyses (`reference-content/2026-09-10`), translated to
generic tiers (Frontier/Mid/Cheap/Human/External/Verifier/Environment).
Rule: this file is updated — items reordered, rescoped, or parked — whenever an item's
results change what the next item should be. Conditions below are binding, not advisory.

## State (2026-09-10, P1 pushed; P2 COMPLETE — pushing)
- WQ1 DONE/PASS (84/84, zero recombine; `tools/contrib_taxonomy.py`, `wq1_contrib.md`).
  Condition B not triggered. WQ2/WQ4/WQ5 unlocked.
- WQ1b DONE/CLEAN (floorless test cannot fire on stored data; both defs run in WQ4).
- WQ2 DONE/PASS on EV (+0.046/cell; per-seed +0.104/+0.104/−0.070;
  `tools/fitness_gate.py`, `wq2_fitness.md`). Router integration QUEUED.
- WQ6 DONE (additive `stack` param + `stack_assumed` stamp; tests 30/30).
- WQ3 DONE/PASS 27/27 zero-compute (signed kept-gap tripwire; invert trips 9/9,
  blind silent 18/18; margin tracks recovery; `tools/margin_tripwire.py`,
  `wq3_margin.md`). Gaming-stress calibration still open (needs poison runs).
- WQ4 DONE (`flywheel_pkg28.py`, `pkg28_eco.json`, `pkg28_eco.md`): gate FAILs on
  probe-hard (solo-frontier specialist dominance, CIs overlap anyway); R0 separation
  win (joint coverage 3/3 slices, no solo holds all; eco > consult on t2 via depth
  purity — D rejected); depth mechanism (probe variance lives in reason_depth, not
  tier skill); esc channel silent; R1 unrepresentable-in-substrate; Condition B
  untriggered (no recombine hits). v1 consult≡eco identity caught+fixed as spec
  defect before analysis.
- WQ5-sim DONE (`flywheel_pkg29.py`, `pkg29_dose.json`, `pkg29_dose.md`): mass→skill
  (threshold ≤2 arts), length→depth, probe ≈ skill^depth compounding. SFT motive
  narrowed to long-chain dose (CONSULT-2 when raised).
- Round4 audit amendments (binding, applied to pushed text): R0 reframed as
  pool-channel refinement (NOT anti-consult pushback); eco>consult labeled
  directional (Wilson-overlapping); headline triple (no emergence [status: not
  demonstrated] / no on-slice superiority [144-vs-12 caveat] / joint-coverage
  benefit); critique-channel marked UNTESTED (esc=0); graft≈eco explained via skill
  saturation; adversarial checklist in `pkg28_eco.md`; router doc carries
  prior-not-detector + per-seed EV.
- Queued follow-ups (round5 decision: FIRE (ii) first + (i) alongside; HOLD (iii);
  PhaseCAL parked unanimously): (i) skill-margin run — low-skill generator +
  length-matched pools (identifies compounding interaction; pkg30); (ii)
  per-slice-budget-matched ecosystem comparison — DESIGN FIRST (total-cost vs
  per-slice answer different questions; total-cost frame is the external-facing one,
  per-slice the diagnostic; pkg28b flag); (iii) CONSULT-2 brief HELD until (i)/(ii)
  land — required questions pre-listed (transfer theory: why long-trace SFT raises
  hard probe where short-trace doesn't; length-at-matched-mass design; GPU budget).
  Round5 outcome: (i) DONE (`flywheel_pkg30.py`, `pkg30_skillmargin.md`) — depth-margin
  NULL at low skill too; interaction by contrast (depth binds only at saturated skill);
  sequencing skill-first-then-depth. (ii) DONE (`--per-slice`, `pkg28b_perslice.md`) —
  eco ties solo-frontier exactly, holds all slices; purity premium replicates outside
  the budget confound; report BOTH matchings henceforth. (iii) CONSULT-2 brief
  RAISED round6 (GPU approved; `consult2_brief.md` + `tools/colab_harddose_*.py`:
  seeds [0,1500,3000] × {mixed anchor, hard bundled} × 3ep→5ep chained).
  Bank constraint: length≡tier, so length-isolation out of scope (queued: short-hard /
  long-easy bank extension). pkg30 corrected: second ~0.85 sample, not low-skill test.
  Forwarding posture (binding): FAIL primary, R0 secondary — any CONSULT-0
  forwarding leads with gate-FAIL, never R0-first.
- P2 plateau = WQ3 + WQ4 + WQ5-sim. NEXT: P2 push → CONSULT-0; PhaseCAL stays parked
  (trigger, strengthened round4: external readers disagree about what WQ4 DEMONSTRATES
  in a way untraceable to ordinary interpretation differences — not mere importance
  disagreements; if ever run: read-only, interpretation lock, A/B/C classes).

## Round2 amendments (2026-09-10, 7 analyses; binding)
CONSULT-0 and CONSULT-1 both returned. Nods with amendments — incorporated below.
- **Freeze**: EPS/DELTA/FLOOR/HIGH/CEIL + GATE=0.05 frozen as of P1. No retuning once
  WQ4 data exists; WQ4 is the out-of-sample check (claude).
- **WQ1b (before WQ4)**: second recombine test without floor requirement
  (`c >= pb + DELTA`, both parents < HIGH); must stay clean on pkg21/24, reported
  separately (claude). Near-boundary (±DELTA) batch calls route to "drift, contested"
  via Wilson machinery, not bare threshold (claude). Relabel: recombine =
  multi-source joint accessibility (channel), not "weight-level" (glm, grok).
  Add `amplify_pool` vs `amplify_other` sub-tag (deepseek). Matched-pool P1 cell still
  open (deepseek attribution gap — pool also differed in pkg24).
- **WQ2b (before router integration)**: per-seed EV beside pooled mean — measured:
  s0 +0.104, s1500 +0.104, s3000 −0.070/cell (claude, deepseek, glm). Measured-pollution
  flag (fork-time kept-correct of suspect branch, already computed for pair_coverage)
  as primary signal, structural veto as fallback; recompute from existing JSONs, zero
  new runs (glm). Tainted-history decay/rehabilitation after N clean rounds specified
  at design level; calibrate on WQ4 multi-round data (gemini). Router integration stays
  QUEUED until WQ2b revalidates.
- **WQ4 spec (frozen by round2 consensus, 6/7 role nod)**:
  Tiers = capability profiles over slices, all tiers generative (deepseek dissent
  adopted over pipeline-function framing): Cheap broad-shallow volume, Mid narrow-deep
  correctness, Frontier deep-narrow specialty + blind spot, t2≈0.75 headroom so
  screening stays necessary (glm, qwen). Frontier = frozen capability-parameterized SM
  (unanimous), never trained within arms (frozen-first isolates amplification of a
  fixed expert signal); recognition-vs-generation separately parameterized (luna-R1);
  scarcity quotas (cheap ~1000 / mid ~100-200 / frontier ~10-30 calls, luna-R2).
  Frontier role = seed + critique, NOT critique-only (critique-only never touches the
  pool = theater per pkg11/12; claude, glm): scarce golden generations to pool
  (pkg23-style) + disagreement-triggered critique (fires on Mid×Verifier disagreement,
  sparing by construction). Mid = pool-construction AND selection instrumented
  separately (claude, pkg11 lesson).
  Arms: 3 solo + 3 pairwise + ecosystem (7×3 seeds); matched TOTAL generation budget
  across arms (glm); solo arms double as classifier parents — recombine comparison is
  ecosystem-child vs solo-children, never vs tier SMs (glm, deepseek); strongest solo
  control = cheap + free rule screen (pkg22-C pattern). Optional graft-merge arm
  (per-slice max params; consult ceiling as trainable artifact; glm).
  Endpoints: probe-hard primary (rematch) + NOVEL/KNOWN co-primary (consult: NOVEL-null
  recombine hit = amplification, not emergence) + taxonomy classes; coverage/NOVEL
  co-primary so both WQ4-condition branches stay informative. Formal gate (luna-R2):
  C_eco > max(C_solos, C_consult, C_harvest[, C_graft]) on held-out. R0/R1 ladder +
  outcomes A–E pre-registered. Channel annotation for any bank data (glm). Log judge
  margins per round regardless of WQ3 state (glm → WQ3 calibration data). Recombine
  = channel joint-accessibility on current substrate (substrate change explicitly
  rejected unless stage-1 shows unrepresentability per deepseek option C; first
  recombine hit gets P0 forensics per Condition B).
- **Quarantined from doctrine**: marketplace/token-layer specifics (pre-result spec,
  unmeasured); any synthesis still treating evaporation as family law / merge as
  internalization / regret as selector (tainted-history watch).

## PhaseCAL — Meta-family internal calibration (PROPOSED, separate phase)
Opportunity: relative-volume calibration across Muse Spark 1.3 (this session) / 1.2 /
1.1-web. Engaged only if it beats queue progress. Fitting points, in order:
  (a) WQ4 spec frozen — calibrate spec-reading across versions (cheap, no runs);
  (b) WQ4 results landed — calibrate interpretation on novel data (the real test:
      do versions converge or diverge where no archor exists?).
  Order: (b) primary, (a) optional. Never interleaved with WQ4 runs (would confound
  the out-of-sample check). Prompter forwards data externally; results return as
  reference-content. Parked until WQ4 spec freeze — raised in TUI then.

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

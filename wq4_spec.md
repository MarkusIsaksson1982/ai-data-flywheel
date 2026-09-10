# WQ4 spec — heterogeneous-ecosystem sim (FROZEN 2026-09-10, pkg28-ecosystem)

Status: FROZEN by round2 consensus (6/7 role nod) + round3 amendments below.
Rule: no retuning once WQ4 data exists. Amendments only for spec defects
(literal inconsistency / impossible implementation); preferences defer to variants.
(27 stays the archived veto-collapse doc; WQ4 builds as package 28.)
Thresholds frozen: EPS=0.02, DELTA=0.05, FLOOR=0.35, HIGH=0.60, CEIL=0.90, GATE=0.05.

## Round3 amendments admitted (spec-defect class only)
1. Formal gate is significance-gated: `C_eco > max(...)` requires non-overlapping
   CIs or effect past the ~0.05–0.08 batch-noise band — never a bare point estimate
   (claude). Headline verdict inherits the Wilson discipline.
2. Stage-1 fix: substrate change is PRECONDITION for stage-1, not consequence.
   Stage-1a (current substrate, hand-constructed complementary pair, no router):
   pass = channel-recombine fires (expected via mass channel; if silent, ecosystem
   runs Pareto-framing only). Stage-1b (2D-profile substrate probe): decides whether
   the R1 compositional arm is representable; if not, reported
   `unrepresentable-in-substrate`, never "not observed" (deepseek).
3. Budget protocol: N matched at solo-comparison level — each solo arm gets total N
   in its own tier; ecosystem gets the same total N distributed per tier weights.
   The distributional-vs-concentrated comparison is intended and stated (deepseek).
4. `inherited-from-Frontier-frozen-pool` channel tag alongside amplify_pool (deepseek).
5. Outcomes A–E pre-registered below; cheap+free-screen solo is a registered outcome,
   not a surprise (deepseek). Graft labeled `graft-ceiling`, never a gate target;
   graft inputs pass the fitness gate like everything else (claude, deepseek).

## Tiers (capability profiles over slices; ALL tiers generative)
- Cheap: broad-shallow, high volume, low per-slice correctness; archive mass on easy/med.
- Mid: narrow-deep, fewer traces, higher correctness on med; pool-construction AND
  selection instrumented SEPARATELY (pkg11 lesson).
- Frontier: deep-narrow specialty + deliberate blind spot; t2≈0.75 headroom (makes
  screening necessary; at 0.95 Mid collapses into redundancy). FROZEN within arms
  (never trained — isolates amplification of a fixed expert signal; co-evolution is
  the follow-up). Capability-parameterized SM with recognition-vs-generation split
  independently parameterized. Scarcity quotas (~1000 / 100–200 / 10–30 calls).
- Verifier stays free, outside the model-tier comparison. Bank = annotated channel.

## Frontier role: seed + critique (never critique-only = theater, pkg11/12)
Scarce golden generations directly to pool (pkg23-style) + critique triggered by
Mid×Verifier DISAGREEMENT (sparing by construction). Judge routing with zero new
machinery: cheap stream judged by Mid SM, t2 candidates escalate to Frontier
(`evaluate_v4` takes arbitrary judge_sm). Log judge margins per round (WQ3 data).

## Arms (7 + optional graft) × 3 seeds, matched total budget
Solo cheap / solo mid / solo frontier (+free rule screen everywhere; strongest solo
control = cheap + screen, pkg22-C pattern) + 3 pairwise + ecosystem + [graft-ceiling].
Solo arms double as classifier parents: recombine comparison is ecosystem-child vs
solo-children, NEVER vs tier SMs. Both recombine definitions run and report separately
(floored + floorless/WQ1b). Near-boundary calls → "drift, contested" (Wilson).

## Endpoints (all pre-registered)
Probe-hard PRIMARY (rematch). NOVEL/KNOWN co-primary (consult: NOVEL-null recombine
hit = amplification, not emergence). Taxonomy classes on solo-children comparison.
Coverage + NOVEL co-primary (both WQ4-condition branches stay informative).
Formal gate: C_eco > max(C_solos, C_consult, C_harvest[, C_graft]) on held-out,
significance-gated per amendment 1.

## R0/R1 ladder + outcomes A–E (pre-registered)
R0 amplificatory combination (coverage/routing, already-present capability mass);
R1 genuine compositional recombination (X+Y→Z, not in either parent's accessible mass).
A: frontier-critique decisive. B: mid captures ~all benefit (frontier unnecessary).
C: frontier helps only with heterogeneous archive (interaction effect). D: apparent gain
disappears vs retrieval controls (masquerade — most valuable negative). E: novel
compositional capability, unretrievable (strongest positive).
P0 forensics on ANY recombine hit: mass channel must be shown in rebuilt pools
(pkg22 pattern); hit without mechanism reopens consult (Condition B).

## Open side-cells (do NOT block build)
Matched-pool P1 attribution cell (deepseek). Tainted-history decay calibration uses
WQ4 multi-round data (gemini). R1 compositional task substrate per stage-1b verdict.

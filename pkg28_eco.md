# Package 28 — Heterogeneous ecosystem: gate FAILs; R0 refines (not rebuts) pool-channel

## Headline triple (round4 audit response — read all three, not one)
1. **No emergence**: formal gate FAILs on probe-hard all seeds (solo-frontier
   0.875/0.812/0.875 beats joint-eco 0.625/0.625/0.750; Wilson CIs overlap
   regardless). Status: NOT DEMONSTRATED, not demonstrated-absent — the NOVEL
   co-primary was degenerate (n=3–9, at ceiling), so emergence defaulted through
   the gate rather than being directly tested.
2. **No on-slice superiority**: per-slice budget is 144-vs-12 asymmetric
   (solo-frontier spends everything on t2; eco spends 12 frontier calls) — the FAIL
   is partly the gate's question, not just the ecosystem. Specialists beat
   generalists on-slice; expected, pre-registered risk.
3. **Genuine joint-coverage/division-of-labor benefit**: eco holds 3/3 slices ≥HIGH
   all seeds; NO solo does. Plus the R0-separation directional below.

## Design (spec `wq4_spec.md` frozen; one spec-defect disambiguation in build)
Tiers = capability profiles, all generative, specialist diets (cheap {0,1} / mid {1} /
frontier {2}), frozen parameterized Frontier (t2 0.75, blind spots), matched N=144
budget (eco 102/30/12), 3 solo + 3 pair + ecosystem + consult (Mid + union pool) +
graft-ceiling × 3 seeds, G0–G2 specialization, arms G3–G6. Frontier = scarce seeds +
disagreement-triggered critique (trigger NEVER fired: esc=0 all arms/rounds — clean
regime has no Mid×rule disagreements > 25; margins ~0.7–1.2 logged flat for WQ3).
Disambiguation (build log, category B): v1 trained one mid line for ecosystem AND
consult (bit-identical) — core comparison vacuous. Ecosystem = THREE specialist
lines + JOINT per-slice-max endpoint; consult = one mid line on union pool.
`python flywheel_pkg28.py` → `pkg28_eco.json`. Stage-1a 3/3 PASS (joint t0=0.97,
t2=0.804). Stage-1b: compositional R1 unrepresentable in current bank (no skill
interaction in correctness draws) — reported, not coded.

## Result 1 — formal gate FAILs on probe-hard (see headline triple above)
G6 probe-hard: solo-frontier beats joint-eco on all seeds (Wilson CIs overlap
regardless). NOVEL split degenerate — emergence rests entirely on the failed gate.
Frontier-as-critique UNTESTED (esc=0 everywhere): the bound is on seed-only
Frontier; whether the critique channel adds value needs a regime where the trigger
pulls (poison / Mid×rule disagreement). "Dual role tested" claims withdrawn.

## Result 2 — the depth mechanism (in-sim variance statement; narrow export)
Tier_acc[2] ≈ 0.94–1.0 in ALL t2-practicing arms — tier skill saturated — yet probe-hard
spans 0.312→0.938. The variance lives in reason_depth (pool chain-length
distribution), NOT tier skill:
solo-frontier depth 3.08–3.09 → probe 0.812–0.875; eco frontier-line 2.37–2.55 →
0.625–0.750; consult 2.07–2.12 → 0.312–0.688; pair-MF 2.45–2.64 → 0.688–0.938.
Mechanism: big-batch top-k selects long flawless chains (depth target high); thin streams
take what they get (short chains → depth sags) — SAME tier skill, different depth.
Corollary: pkg23's "thin supply suffices" holds for tier_acc and FAILS for depth.
Export discipline: `probe ≈ skill^depth` is a curve fit to this sim's per-step
compounding, NOT a general law (skill margin never independently varied — queued:
low-skill generator + length-matched pools). The generalizable candidate is narrower:
POOL COMPOSITION AFFECTS NON-TIER PARAMS (which slices get practiced → tier skill;
what chain-length regime survives → depth). Vocabulary: depth = accumulation within
supported capability; skill = acquisition beyond the retrieval regime (the latter
unobserved here — nothing in P2 acquired capability unavailable to supply).
Mass-vs-length decomposition: pkg29 (mass→skill ≤2 arts; length→depth).

## Result 3 — R0 separation (refines pool-channel skepticism; directional, not significant)
Joint-eco t2 probe 0.625/0.625/0.750 vs consult 0.500/0.312/0.688 (directional 3/3,
Wilson CIs overlap — LABELED directional; the gate is held to Wilson, this claim is
not significance-gated and must not be read as if it were): separated pure pools
preserve depth that mixed-pool training dilutes. Framing correction (round4): this
does NOT push back on the merge verdict (both arms retrieval-based; weight-surgery
skepticism intact) — it DEEPENS pool-channel doctrine: layout matters within the
channel (scaling extension of pkg11/12: union pooling dilutes each specialist's
signature supply). Per-slice taxonomy vs best solo: preserve/preserve/degrade (joint
t2 < solo-frontier t2) — correctly refuses recombination. Joint coverage (tiers≥HIGH):
eco 3/3 slices all seeds; NO solo holds all three — joint-accessibility fires as R0
coverage win.
Graft ≈ eco (0.562–0.688) explained, not hand-waved: both sit at saturated tier skill
(0.996); at saturation the arms are numerically near-equivalent and the residual spread
(±1–3 probe items, inside noise) is depth second-order. No new mechanism required —
and this bounds eco's edge over consult the same way.

## Adversarial checklist for the R0 claim (round4: invite breakage, not applause)
- Hidden pool-content differences: open by construction (layout IS the treatment).
- Curriculum differences: intended treatment (specialist diets), not confound.
- Evaluator-induced selection: same blind judges everywhere; cross-tier judging
  symmetric across arms using it. No asymmetry found.
- Bank leakage: bank EXCLUDED from all pools by design (channel annotation trivial).
- Capability-dependent supply: present (specialists supply own slices) — the
  mechanism, not a confound; thin-supply saturation documented (pkg23).
- Unequal exposure (144-vs-12 per-slice asymmetry): ACKNOWLEDGED, open — a
  per-slice-budget-matched follow-up would separate "specialist wins on-slice"
  (budget artifact) from "ecosystem wins coverage" (actual claim). Queued, unrun.
- Other channels: graft-ceiling ≈ eco bounds the params channel; esc=0 bounds the
  critique channel (untested, not excluded).

## Verdict mapping (pre-registered A–E + R0/R1)
E rejected (gate). D rejected (eco > consult directionally — structure adds beyond
access). R0 FIRES (joint coverage no solo holds + purity premium). R1
unrepresentable-in-substrate. B/C not observed. P0 forensics: no recombine hit
anywhere (taxonomy clean) — Condition B untriggered.
net: division-of-labor sourcing + union/separated pooling beats self-loops;
separation beats blending; specialists beat generalists on-slice. No emergence.

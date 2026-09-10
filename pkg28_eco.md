# Package 28 — Heterogeneous ecosystem: R0 separation win, gate FAILs as specified

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

## Result 1 — formal gate FAILs on probe-hard (specialist dominance, pre-registered risk)
G6 probe-hard: solo-frontier 0.875/0.812/0.875 beats joint-eco 0.625/0.625/0.750 on all
seeds (Wilson CIs overlap regardless). A t2-specialist self-loop wins its specialty;
no emergence (E rejected). NOVEL split uninformative (novel n=3–9, acc 1.0 at ceiling
in full-diet arms; solos' novel = off-diet items) — emergence test defaults to gate.

## Result 2 — the depth mechanism (new, measured, explains everything)
Tier_acc[2] ≈ 0.94–1.0 in ALL t2-practicing arms — tier skill saturated — yet probe-hard
spans 0.312→0.938. The variance lives entirely in reason_depth (pool chain-length
distribution), NOT tier skill:
solo-frontier depth 3.08–3.09 → probe 0.812–0.875; eco frontier-line 2.37–2.55 →
0.625–0.750; consult 2.07–2.12 → 0.312–0.688; pair-MF 2.45–2.64 → 0.688–0.938.
.modal: big-batch top-k selects long flawless chains (depth target high); thin streams
take what they get (short chains → depth sags) — SAME tier skill, different depth.
Corollary: pkg23's "thin supply suffices" holds for tier_acc and FAILS for depth.
Mass-vs-length decomposition open (WQ5-sim owns it).

## Result 3 — R0 separation win (structure beats union data on t2, D rejected)
Joint-eco t2 probe 0.625/0.625/0.750 vs consult 0.500/0.312/0.688 (directional 3/3):
separated pure pools preserve depth that mixed-pool training dilutes. The ecosystem
gain does NOT disappear against the retrieval control — pool-channel skepticism
answered, but as ROUTING (separation), not emergence. Per-slice taxonomy vs best
solo: preserve/preserve/degrade (joint t2 < solo-frontier t2) — the taxonomy
correctly refuses to call this recombination. Joint coverage (tiers≥HIGH): eco 3/3
slices all seeds; NO solo holds all three (cheap t2 floor/missing, mid t0/t2 missing,
frontier t0/t1 missing) — joint-accessibility fires as R0 coverage win.
Graft ≈ eco (0.562–0.688): ceiling behaves as ceiling.

## Verdict mapping (pre-registered A–E + R0/R1)
E rejected (gate). D rejected (eco > consult directionally — structure adds beyond
access). R0 FIRES (joint coverage no solo holds + purity premium). R1
unrepresentable-in-substrate. B/C not observed. P0 forensics: no recombine hit
anywhere (taxonomy clean) — Condition B untriggered.
net: division-of-labor sourcing + union/separated pooling beats self-loops;
separation beats blending; specialists beat generalists on-slice. No emergence.

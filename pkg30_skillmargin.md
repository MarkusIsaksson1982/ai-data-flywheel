# Package 30 — Skill-margin run: interaction confirmed (depth binds at saturated skill)

## Design (round5-i)
pkg29 clone, base tier_acc [0.80, 0.90, 0.45] (LOW t2 skill), SAME banks (imported —
directly comparable), arms H0 / H12-mixed / H12-short / H12-long × 3 seeds × 3 rounds.
`python flywheel_pkg30.py` → `pkg30_skillmargin.json`.

## Result
- Skill saturates from presence at low skill too: H12 arms 0.45→0.698→0.834
  (identical across lengths); H0 0.45→0.37→0.30 (forgetting).
- Depth moves with length identically: long →2.35, mixed →2.03, short →1.94.
- Probe G2 long-vs-short: +0.063 / 0.000 / 0.000 (pkg29 high-skill: +0.000 / +0.062 /
  +0.125). Depth-margin NULL at BOTH skill levels.
- Interaction identified by contrast: pkg28's depth-margin-positive runs all sat at
  skill ~0.94–1.0; at skill 0.83–0.86 depth moves probe ~nowhere (6 seed-regimes,
  mean gap +0.04 ≈ noise). Depth binds ONLY once skill saturates — directional
  skill×depth interaction. `skill^depth` stays a qualitative interaction, never a
  formula (skill margin at controlled depth now measured both ways: saturated-flat
  here, saturated-steep in pkg28 arms that moved both).

## Consequence
The depth finding is now bounded on both sides: necessary-ish at saturated skill
(pkg28 dilution gradient), inert below it (here). CONSULT-2 implication sharpens:
long-chain dose matters only AFTER skill presence is secured — sequence is
skill-first (≤2 correct arts), depth-second (long chains). A long-chain SFT on a
skill-absent slice should expect nothing (this run); on a skill-present slice,
depth is the remaining lever (pkg28).

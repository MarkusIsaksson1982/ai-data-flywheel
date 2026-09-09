# Package 21 report — Divergent merging works; gates agree; per-slice gate unproven

9 combos (single / scalar-merge / slicemerge × seeds 0/1500/3000; shared G0,
specialist branches G1–G3, fork G4, continue G4–G7). Data: `pkg21_merge.json`
(collapse-protocol variant discussed in design was not run — see §5).

## 1. Null post-mortem that made this run necessary.

First attempt diverged pools only, keeping shared plain top-18 selection: both
branches kept identical easy+med sets (hard 0 everywhere), complementarity was
vacuous, all arms identical. Lesson recorded in code: specialization must span
selection, not just pools. Fixed design uses branch quotas (E: easy+med,
H: med+hard) and produces mirror specialists (E ≈ [0.93,0.93,0.31],
H ≈ [0.31,0.93,0.84]) with scalar complementarity 0.676–0.795.

## 2. Merging complementary specialists beats best-single continuation.

G7 hard skill: single 0.30 (floored, all seeds) vs merged 0.708 (all seeds);
hard corr 0.19–0.29 vs 0.25–0.40; easy/med within ±0.01 (dilution trace only).
The merge gain is large, consistent, and mechanistically clean (access to the
other lineage's practiced slice). Endpoint probe (post-hoc regeneration, n=8
per tier): hard 0.125–0.25 all arms, no separation — directionally consistent
but underpowered; not claimed as confirmation.

## 3. Scalar gate validated; per-slice gate indistinguishable.

Scalar fired on all divergent pairs (0.676–0.795 > 0.5) and refused all
same-lineage pairs in the null run (0.357–0.5) — but Thread-C records
same-lineage values up to 0.73, so the ranges overlap and 0.5 will occasionally
merge same-lineage pairs. Kept at 0.5 anyway: observed cost of false-positive
merges is ~0 (v1 same-lineage merges ≈ null; here −0.01 easy worst case).
Scalar vs per-slice gate: both merged everywhere with bit-identical downstream
trajectories — the per-slice gate is UNPROVEN as an improvement, not refuted.
Blocking issue found inside it: C_pair hits 1.0 whenever recent cells are each
tier's best (max-over-pair ≡ max-over-lineage-best), so as implemented it
cannot discriminate; fix specified (lineage-best wider than the pair, absolute
scale) but not run. A genuine disagreement case (high pid-overlap with
divergent quality, or vice versa) is the specified next discrimination test.

## Decision.

REJECT routine merging (single-parent default stands); KEEP the scalar 0.5
gate (fires meaningfully, false positives costless); per-slice gating and
C_pair stay experimental pending a disagreement case; collapse-robustness of
the merge gain unrun and open.

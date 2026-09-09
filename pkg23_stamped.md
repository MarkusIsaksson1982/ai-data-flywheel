# Package 23 — Tier-stamped golden: anti-forgetting backstop, not super-teacher

## Question (pkg22 residue)
pkg22-C's untiered golden backfill froze hard gains (~0.72) instead of extending them.
Does tier-stamped golden teach — resume the climb — or also merely hold?

## Design
Identical disease prefix (pkg22 `run_prefix`: misc .35 + invert pure0, G0–G4, same guards),
fork G5–G9 (extended two rounds past pkg22's G7 to separate teaching from preserving).
Selection uniform plain top-72, judge invert throughout. Only the pool differs:
- **unstamped** (pkg22-C replication): screened quota 12/12/12 + untiered golden backfill
- **stamped** (test): screened quota 12/12/12 + tier-stamped golden backfill (36 correct
  arts, 12/tier, from the procedural bank via skilled SM, rule-verified; shared archive)
3 seeds × 2 arms. Bar: hard acc ≥ 0.80 by G9 (above the 0.72 freeze).

## Result: stamped wins by preventing forgetting, not by raising the ceiling

| seed | G9 acc2 stamped | G9 acc2 unstamped | probe-hard |
|---|---|---|---|
| 0 | **0.953** | 0.758 | 0.500 vs 0.438 (G8: 0.625 vs 0.125) |
| 1500 | 0.950 | 0.950 (bit-identical) | 0.688 both |
| 3000 | 0.951 | 0.910 | 0.625 vs 0.438 |

Tier-2 pool fill (local+garden, per G5–G9) tells the whole story:
- s0 unstamped fills: 9 / **0 / 0** / 5 / 12 → two unpracticed rounds → acc2 sags
  0.72 → 0.64 → 0.56, recovers only to 0.758. Stamped fills 9/11/6/12/12 → climbs
  monotonically to 0.953.
- s1500 unstamped fills never hit 0 (5/3/9/12/12) → trajectories bit-identical.
- s3000 unstamped fills 3/0/1/10/12 → one zero round → partial gap (0.910 vs 0.951).

## Mechanism (read off `train_next_sm` + data, no new machinery)
1. The screened quota guarantees sub-pool correctness c≈1.0 for every *practiced* tier in
   both arms — so practiced tiers update identically whether the practice came from live
   supply or stamped golden. Hence the bit-identical s1500 arms.
2. Golden tier keys matter exactly where local screened supply is **zero**: stamped golden
   practices the tier (c=1.0), unstamped hits the `else: forget −0.08/round` branch.
3. The ceiling (~0.95) is set by local supply, never exceeded by golden: stamped is a
   **backstop against forgetting**, not a teacher above supply.
4. Dose-response in zero/thin rounds: 0 supply → forget; even 1–3 screened arts practice
   fully (s1500-G6 fill=3, no sag). Misc declines monotonically in all arms (≤0.015).

## Doctrine delta
- Golden archives should be **tier-stamped**; stamp value ∝ scarcity of local screened
  supply per tier. Backfill **only empty tiers** — thin live supply (≥1 art) already
  practices fully, so redundant golden wastes pool slots (no harm observed, but no gain).
- Correction to pkg22 read: unstamped golden doesn't "freeze" gains — extended to G9 it
  sags-then-recovers as local supply returns; pkg22 stopped at G7 mid-sag.
- Program-level: third straight win for "the pool is the product" (consult null on merge
  weights, pkg17-D screened-supply recovery, now stamped-golden practice). Harvesting
  works through pool composition (practice + supply), not weight surgery.

## Repro
`python flywheel_pkg23.py` → `pkg23_stamped.json` (3 seeds × (prefix + 2 arms × 5 rounds)).
Golden: 36 arts, all rule-correct. `OUT` block `"stamped"`.

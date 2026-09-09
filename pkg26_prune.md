# Package 26 — Fallback hygiene: prune the vetoed history (one-line fix, exact kill)

## Question (pkg24 residue)
Fallback-to-single trailed pure single because G5+ pools kept drawing on the vetoed
branch's history. Fix: drop the vetoed branch's history from `kept_hist` on fallback.

## Design
pkg24-v2 fork verbatim (asserted scalar=1.0>0.5, gain=0.0≤0.05 all seeds), arms G4–G7:
single (E hist), pruned (E hist — same object, different arm tag), polluted (E+W hist).
`python flywheel_pkg26.py` → `pkg26_prune.json`.

## Result: exact kill, front-loaded mechanism

| seed | G7 med single | G7 med pruned | G7 med polluted |
|---|---|---|---|
| 0 | 0.917 | 0.917 | 0.771 |
| 1500 | 0.958 | 0.958 | 0.896 |
| 3000 | 0.792 | 0.792 | 0.917 (washes out) |

- **pruned ≡ single**: all round metrics, attempted problem sets, and kept pid sets
  identical across all seeds/rounds (artifact ids differ only by the arm tag embedded
  in id strings; model version/lesson strings likewise cosmetic). The fix is exact.
- **Mechanism, front-loaded**: polluted G4 pool is 50% W arts (stale invert-inflated
  scores outrank fresh blind scores), dropping to 0% by G5 as fresh history buries it —
  yet the single deflected G4 training round bends the whole trajectory (s0/s1500 never
  recover; s3000 washes out). One bad pool round is enough; there is no safe level of
  vetoed-history contamination to "average out."
- Replicates pkg24's slicemerge numbers exactly (same fallback path), now with the
  cause isolated to pool history (weights were always E-only here).

## Doctrine delta
- **On any gate veto/fallback, prune the vetoed branch's history from the training
  pool, not just its weights.** Veto must cover data lineage, not the merge op.
  One-line rule; zero cost; exact effect.
- Pool-half-life note: stale mis-scored arts dominate exactly one training round post-
  veto, then vanish under fresh history — so pruning matters most at the first
  post-decision round; audit pools there.

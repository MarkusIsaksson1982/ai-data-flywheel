# pkg19 — Capability Frontier Ledger: Retro-Analysis Report

## Overview

This report documents the **pkg19-style retro-ledger**: a zero-new-compute
analysis that rebuilds the capability (C) and importable mass (M) matrices
from already-logged harness/pkg rounds. The ledger determines whether the
harvesting thesis is empirically supported before any policy change is
proposed.

## Motivation

The core question is whether aggregate metrics systematically understate
the value of past-generation capabilities. Six external model reviews
converged on the ledger as the formal object that the repo's existing
mechanisms have been approximating:

- Per-tier pool quotas
- Utility / forgotten-term import
- Complementarity-gated merge
- Bottleneck mass accounting

Making the object first-class lets those four mechanisms be compared,
gated, and validated against one another instead of remaining independent
heuristics.

## Methodology

### Data Sources

All logged round data is read from existing JSON files in the repo
(`pkg*.json`, `harness*.json`). No new simulation runs are required.

### Matrix Construction

**C Matrix (Capability):** For each generation *g* and slice *i* =
`(problem_id, tier)`:
- ĉ_g(i) is estimated from `tier_acc` per round, using fresh-seed probe
  measurements (never from training artifacts)
- Wilson score intervals provide significance bounds
- Each entry records `est`, `n`, `ci_lo`, `ci_hi`

**M Matrix (Importable Mass):** For each generation *g* and slice *i*:
- M_g(i) = count of correct, hard (tier=2), kept artifacts minus quarantined items
- This is the actual recoverable asset per slice

### Frontier Detection

For each slice *i*, the frontier holder is:
- F(i) = argmax over g ≤ t of ĉ_g(i)
- **Significance gating**: a flip requires non-overlapping Wilson intervals
- Without gating, the ledger churns on noise (FDR discipline is not optional)

### Key Statistics

1. **Non-Dominated Share (NDS):** Fraction of slices where the final
   generation is NOT the frontier holder.
   - NDS ≈ 0 → harvesting is empirically empty in this regime
   - NDS material → subsequent experiments are well-motivated

2. **Dormant Frontier Census:** Frontiers where F(i) = τ but M_τ(i) = 0.
   Capability lives in weights but archive was pruned → parameter-level
   harvesting required.

3. **Aggregate Understatement:** How often aggregate metrics understate
   past-generation value, quantified by comparing per-slice frontier
   estimates against what the latest generation alone reports.

## Results Template

After running `python flywheel_ledger.py` or `python tools/make_ledger.py`:

```
Generations: [G0, G1, ..., Gn]
Slices: N (= 36 for hand bank, 48+ for procedural)
NDS: X.XXXX
Dormant frontiers: Y
Understatement fraction: Z.ZZZZ
```

### Interpretation

| NDS | Meaning |
|-----|---------|
| ≈ 0 | Past generations never hold frontiers in this regime; ledger survives only as regression dashboard |
| 0.1–0.3 | Partial frontier drift; selective harvesting potentially worthwhile |
| > 0.3 | Material past-generation advantage; harvesting thesis strongly supported |

## Measured results (consolidated run, this repo)

Retro tool: adopted `capability_ledger.py` + `retro_ledger.py` (sibling
Muse-Spark implementation; convergent independent implementations by
Ling/MiMo/Nemotron documented but not duplicated — see Consolidation note).
Command: `python retro_ledger.py --logs . --pattern "pkg1*.json" --out <tmp>`,
plus `harness_results.json` and `pkg4_comp.json` passes; outputs directed to
temp (tracked refs/ stays lean per repo policy).

| corpus | runs | mean NDS | understating | dormant | verdict |
|---|---|---|---|---|---|
| harness (shared skills, healthy) | 15 | 0.0 | 0 | 0 | harvesting EMPTY here — ledger is dashboard-only (falsification criterion met in the negative) |
| pkg4 (collapse/recovery) | 12 | 0.25 | 1 | 0 | partial drift |
| pkg10–18 tier regimes (forgetting present) | 96 | 0.413 | 21 | 58 | MATERIAL — harvesting thesis supported |
| nemotron independent reruns (their data) | 21 | 0.81 | — | 38 | same direction, larger magnitude (collapse-heavy corpus); cross-check, not pooled |

NDS=1.0 concentrates in collapse arms (final degraded on all slices);
dormant tier-2 frontiers are near-universally held by G0 with
bank-regenerate-or-adapter paths (acc 0.55-era weights outrank floored
successors with no importable mass) — the ledger rediscovers pkg10/11
structure from a new angle (convergent validity). Cross-check: an independent
Nemotron-3 rerun of the same spec reports mean NDS 0.81 on 21 harness runs
(their rerun data, checksums differ — same direction, larger magnitude).

FDR hardening (ported from the Nemotron session into `capability_ledger.py`
as opt-in `--fdr`, tested in `tests/test_ledger_fdr.py`) reproduces every
number above exactly on current data: Wilson pre-gating already admits only
flips with p far below BH thresholds. Numbers pinned in
`refs/ledger_census.json` (default and FDR columns).

Consolidation note (why one implementation): four sessions produced
convergent CFL implementations (sibling `capability_ledger.py` adopted: only
one with passing tests, consumer functions, demo corpus, and drop-in README;
Ling/MiMo/Nemotron variants cited, not duplicated). Big Pickle's test file
targets a fifth, unsupplied API (`TIERS`, `wilson_lower`, …) and was excluded
after failing 15/15 against the adopted module — documented, not silently
dropped. Nemotron's 44KB report + 488KB ledger.json stay in-session (generated
data policy); its headline numbers are cited above.

## Integration with Existing Mechanisms

### Regret-Weighted Import
The current utility pool's binary forgotten term is a step function of the
ledger's regret. The ledger provides a continuous graded signal:
`U(a) = w_r·R_t(slice(a)) + w_q·final(a)/100 + w_n·nov(a)`

### Per-Slice Complementarity
The scalar 0.5 merge gate becomes a coverage ratio:
C_pair(t,τ) = Σᵢ max(ĉ_t(i), ĉ_τ(i)) / Σᵢ max_{τ'} ĉ_{τ'}(i)

### Harvest-Path Selection
Decision rule per slice (priority order):
1. Archive-import if M > 0 and dose budget permits
2. Merge/adapter if dormant frontier and complementarity clears
3. Bank regeneration if the procedural bank covers the slice
4. Log accepted regret

### Dose Scheduling
The ledger's `dose_cap` field schedules import shares by slice instead of
a global mixture ratio, concentrating clean mass where regret is highest.

## Failure Modes of the Ledger Itself

| Failure | Signature | Countermeasure |
|---------|-----------|----------------|
| Frontier illusion | Holder's margin collapses on rotated probe family | Probe-family rotation |
| Judge-laundered entries | J-class cells disagree across judge versions | V-only doctrine; re-stamp on judge change |
| Ledger lock-in | Import share concentrated on one holder | Archive-share cap; novelty term retained |
| Survivorship bias | Dormant frontiers from pruned archives | M-matrix maintained beside C |
| Significance churn | Flip rate above FDR expectation | Gating + correction |
| Verifier blind-spot asymmetry | Per-generation blind-spot-form frequency skew | Per-generation check |

## Next Steps (pkg20+)

1. **pkg20_regret_import** — Prospective A/B: binary-forgotten vs.
   regret-weighted utility, identical collapse protocol, shared seeds
2. **pkg21_complementarity** — Per-slice complementarity gate vs.
   single-parent baseline; per-slice merge deltas recorded
3. **pkg22_dose** — Ledger-scheduled per-slice doses under poison
   mixtures; does per-slice dosing raise the floor?
4. **Consult control arm** — Add inference-time routing as a control
   for all harvesting experiments

## Conclusion

This retro-analysis settles the empirical premise before any policy change
is proposed. If NDS is near zero across logged runs, the harvesting thesis
is empty in this regime. If NDS is material, the subsequent experiments
(regret-weighted import, per-slice complementarity, dose scheduling)
become well-motivated.

The ledger does not eliminate the known failure modes; it gives them
per-slice addresses. Localization, not elimination, is the deliverable —
and it is enough to make the incident-response doctrine dispatchable at
slice granularity.

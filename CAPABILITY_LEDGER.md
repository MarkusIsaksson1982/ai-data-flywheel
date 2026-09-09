# Capability Frontier Ledger (CFL v0.1)

**Status:** design + working foundation (retro-analysis). Not frozen doctrine.
**Source synthesis:** Grok-fast (lead synthesis + highest-value next step),
ChatGPT-5.6-Luna (L_i tuple, frontier vs inheritance, V_i tradeoff, ecosystem
branches), GLM-5.3 (CFL v0.1 spec this file implements), DeepSeek (matrix +
mixture-of-teachers + guardrail), Qwen3.8-max (phylogenetic framing, MoG
router, archaeology), Mistral-vibe (whitepaper + marketplace), Gemini-3.1-pro
(matrix of forgetting + frontier-biased sampling).

## 1. Claim

In a lineage G₀…G_T aggregate metrics systematically misstate past-generation
value. The correct accounting object is a **pair of matrices**:

- **C(generation × slice)** — measured capability (fresh-seed probes only).
- **M(generation × slice)** — importable correct mass (kept ∩ correct ∩
  non-quarantined), the binding constraint per the bottleneck result
  (pool-correct-hard x=0 → y≤0).

Ledger = (C, M) + significance gating + provenance + quarantine state.

## 2. Definitions

- `ĉ_t(i) ∈ [0,1]` — capability estimate, fixed probe count per cell.
- `F_t(i) = argmax τ≤t ĉ` — frontier holder, **significance-gated**: flip
  requires non-overlapping Wilson-95 intervals, else `contested=True`.
- `R_t(i) = ĉ_F(i) − ĉ_t(i)` — regret (harvestable gap).
- **NDS** — fraction of slices where the final gen is not the holder.
- **Dormant frontier** — `F(i)=τ` but `M_τ(i)=0` (weights hold it, archive
  pruned; data harvest impossible → adapter/merge or bank regeneration).
- **Epistemic class** — V (rule-verifier-anchored, this domain) vs J
  (judge-dependent). J excluded from NDS by default; re-stamp on judge change.

Slice space: **tier (n=3)** by default. `(category × tier)` 36-cell mode is
supported (`--mode catxtier`) but each refinement halves power per cell —
finer axes stay diagnostic until disputes concentrate there.

## 3. Why this fits the repo (not a new program)

Four frozen mechanisms already approximate this object with coarse proxies:

| Mechanism | Current proxy | Ledger upgrade (in code) |
|---|---|---|
| Per-tier pool quotas | fixed 12/tier | deficit weights `w=(1−acc)/Σ`, regret weights |
| Utility/forgotten import (pkg13) | binary forgotten term | graded `U=w_r·R+w_q·final/100+w_n·nov` |
| Complementarity merge gate | scalar 0.5 | `C_pair=Σmax(c_t,c_τ)/Σmax_τ′c` + per-slice deltas |
| Bottleneck mass accounting | pool-correct-hard | per-slice M + dose_cap scheduling |

Making the object first-class lets the four be compared, gated, and validated
against each other. Consumers are implemented as pure functions in
`capability_ledger.py`: `deficit_weights`, `regret_weights`,
`pair_coverage`, `harvest_path_for`.

## 4. Measurement discipline

1. Fresh-seed probes only for C (`probe_tier_corr`, rule_v4). Train recompute
   and `tier_acc` params accepted but stamped `contaminated=True`.
2. Wilson-95 non-overlap gating (this foundation). Full Benjamini–Hochberg
   across S×T is the documented next hardening — currently conservative by
   construction (fewer flips, not more).
3. Cost control (live tracks): freeze retired C, re-probe contested cells only,
   adapt probes to disputes.
4. Verifier invariance assumption is checkable: per-generation blind-spot-form
   frequency tripwire (the `82+91+77+90` multi-add case).

## 5. Schema (`capfront-ledger/v1`)

```json
{
  "schema": "capfront-ledger/v1",
  "slice_space": {"axes": ["tier"], "mode": "tier", "n": 3},
  "generations": [{"id": "comboX-G4", "g": 4}],
  "C": [{"gen": "comboX-G2", "slice": "tier=2", "est": 0.61, "n": 16,
         "ci": [0.46, 0.74], "instrument": "probe", "measured_by": "rule_v4"}],
  "M": [{"gen": "comboX-G2", "slice": "tier=2", "importable_mass": 7,
         "quarantined": 1, "kept_total": 12}],
  "frontier": [{"slice": "tier=2", "holder": "comboX-G2", "status": "trailing",
                "regret_of_current": 0.18, "harvest_path": "archive-import",
                "dose_cap": 0.25}]
}
```

Harvest paths in priority order: `archive-import` (M>0) →
`bank-regenerate-or-adapter` (dormant + regretted) → `accept-regret`
(regret ≤ 0.02). Full rule: `harvest_path_for()`.

## 6. Ledger failure modes (its own tripwires)

Frontier illusion (rotate probe family) · judge-laundered J entries (V-only
doctrine) · atavism lock-in (archive-share cap + novelty term retained) ·
survivorship bias (M beside C) · blind-spot asymmetry (form-frequency check) ·
significance churn (gating) · Goodhart on probes (family provenance logged).

## 7. Falsification (what kills the design)

- NDS≈0 across logged runs → harvesting empty here; ledger = dashboard only.
- Regret-weighted ≤ binary-forgotten (pkg20) → regret effectively binary.
- Per-slice complementarity doesn't predict merge deltas → keep scalar gate.

## 8. Roadmap

- **pkg19 retro-ledger** (this repo: `retro_ledger.py`) — zero new compute.
  Settles NDS / dormant census / understatement before any policy change.
- pkg20 regret-vs-forgotten A/B · pkg21 per-slice complementarity ·
  pkg22 per-slice dose scheduling under poison.
- Branches (deliberately open): MoG inference routing vs distillation
  (harvest must beat consult), subspace/adapter harvesting, cross-family
  ledger (second index, prerequisite for confirmation), failure-frontier
  (negative harvesting), control-theoretic closure (regret supermartingale),
  capability weather map (C heatmap + frontier ridges).

**Bottom line (Grok):** the retro-analysis settles the empirical premise
before any policy change. If NDS is material, regret import, per-slice
complementarity, and dose scheduling become well-motivated.

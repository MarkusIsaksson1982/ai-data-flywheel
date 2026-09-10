"""
Capability Frontier Ledger (CFL v0.1) — foundation
==================================================
Self-contained, stdlib-only accounting object for cross-generational
capability tracking in flywheel-style lineages.

Implements the shared core agreed across six external design drafts
(see CAPABILITY_LEDGER.md) and Grok's "Highest-value concrete next step":
a pkg19-style *retro-ledger* with zero new simulation compute.

  C(generation x slice) — measured capability per slice (fresh-seed probes
      preferred; train-artifact recompute flagged as contaminated).
  M(generation x slice) — importable correct mass per slice
      (kept, correct, non-quarantined artifacts).

Headline statistics:
  NDS (non-dominated share) — fraction of slices where the final
      generation is NOT the frontier holder.
  regret R_t(i) = c_{F(i)}(i) - c_t(i) — harvestable gap.
  dormant frontier — F_t(i)=tau but M_tau(i)==0 (capability lives in
      weights, archive was pruned; data-level harvest is impossible).

Slice space (repo convention):
  Default: tier slices {tier=0, tier=1, tier=2} — the only axis with
  statistical power in logged runs (n~16 probe / ~48 train per tier/round).
  Optional: (category x tier) 36-cell mode when artifacts carry both keys.
  Finer axes (length-bin, template-family) stay as diagnostics, per GLM §1.

Measurement discipline:
  1. Fresh-seed probes only for C (probe_tier_corr). Train-artifact
     recompute is provided but stamped contaminated=True.
  2. Significance-gated frontier flips: Wilson score intervals must not
     overlap, else cell is contested (no holder change). This is the
     FDR-discipline placeholder — full BH correction across SxT is a
     documented extension (see CAPABILITY_LEDGER.md §4).
  3. V-class (rule-verifier-anchored) only in this foundation. J-class
     (judge-dependent) entries are accepted with provenance but stamped
     epistemic_class="J" and excluded from NDS by default.

Determinism: no randomness, no wall-clock, sorted keys, rounded floats.
Drop-in: copy this file + retro_ledger.py into ai-data-flywheel/ root;
  it imports nothing from the repo. Standalone: works on any list of
  round dicts with the documented minimal fields.

Minimal round fields consumed (all optional with graceful fallback):
  round["g"]                     int generation index
  round["metrics"]["probe_tier_corr"]  dict {tier-str: acc} (preferred C)
  round["metrics"]["tier_corr"]        dict {tier-str: acc} (fallback C)
  round["metrics"]["tier_acc"]         list [acc0,acc1,acc2] (param fallback)
  round["metrics"]["probe_corr"] / ["correct_rate"]  aggregate (for
      understatement analysis)
  round["artifacts"]             list of artifact dicts, each with:
      artifact["id"], ["tier"] (0/1/2 or None), ["problem_id"],
      ["correct"] (bool), ["_misc"] (bool quarantine flag),
      ["quarantined"] (bool, alternative flag)
  round["kept_ids"]              list of kept artifact ids (defines archive)
  round["model"]["version"]      generation label (else f"G{g}")

Provenance stamped per C entry: measured_by, instrument, n, contaminated.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

SCHEMA = "capfront-ledger/v1"
DEFAULT_TIERS = (0, 1, 2)
# Documented probe size in pkg10+ (PROBE_BANK 24 problems x NPP=2 = 48 arts,
# 16 per tier). Used ONLY when probe artifacts are not logged (they never
# are in the current repo — only metrics are). Assumption is explicit in
# every C entry (n_assumed=True) so a future probe-artifact log can replace
# it without schema change.
ASSUMED_PROBE_N_PER_TIER = 16
Z95 = 1.96


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def wilson_interval(k: float, n: int, z: float = Z95) -> list:
    """Wilson score interval for binomial proportion. Deterministic.

    k may be fractional (mean*n) — callers pass round(k) implicitly via p.
    Returns [lo, hi] rounded to 3 decimals, clipped to [0,1].
    """
    if n <= 0:
        return [0.0, 1.0]
    p = max(0.0, min(1.0, k / n))
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    lo = max(0.0, (center - margin) / denom)
    hi = min(1.0, (center + margin) / denom)
    return [round(lo, 3), round(hi, 3)]


def _ci_from_acc(acc: float, n: int) -> list:
    return wilson_interval(acc * n, n)


# ---------------------------------------------------------------------------
# Slices
# ---------------------------------------------------------------------------

def slice_key_for_artifact(a: dict, mode: str = "tier") -> str:
    """Map one artifact to a slice key.

    mode="tier" (default): "tier=0|1|2"; artifacts with tier None fall back
        to "cat=<problem_id>" so legacy (pre-tier) runs still ledger.
    mode="catxtier": "cat=<fam>/tier=<t>" where fam is the problem_id alpha
        prefix (e.g. P01 -> P, D0-03 -> D). Tier None -> "tier=X".
    """
    t = a.get("tier")
    pid = str(a.get("problem_id", "?"))
    if mode == "catxtier":
        fam = "".join(ch for ch in pid if ch.isalpha()) or pid
        tpart = str(t) if t in (0, 1, 2) else "X"
        return f"cat={fam}/tier={tpart}"
    if t in (0, 1, 2):
        return f"tier={t}"
    return f"cat={pid}"


def discover_slices(rounds: list, mode: str = "tier") -> list:
    """Union of slice keys observable in metrics or artifacts, sorted."""
    slices: set = set()
    for r in rounds:
        m = r.get("metrics", {})
        for src in ("probe_tier_corr", "tier_corr"):
            d = m.get(src)
            if isinstance(d, dict):
                for k in d:
                    slices.add(f"tier={k}" if mode == "tier" else f"cat=?/tier={k}")
        ta = m.get("tier_acc")
        if isinstance(ta, list) and mode == "tier":
            for t in DEFAULT_TIERS:
                if t < len(ta):
                    slices.add(f"tier={t}")
        for a in r.get("artifacts", []):
            slices.add(slice_key_for_artifact(a, mode))
    # Drop the cat=? placeholder unless it is all we have.
    real = sorted(s for s in slices if s != "cat=?/tier=X")
    tier_only = sorted(s for s in real if s.startswith("tier="))
    if mode == "tier" and tier_only:
        return tier_only
    return real or ["overall"]


# ---------------------------------------------------------------------------
# C matrix (capability)
# ---------------------------------------------------------------------------

def build_C(rounds: list, mode: str = "tier") -> list:
    """Build capability entries. One entry per (gen, slice).

    Source priority per (gen, slice):
      1. metrics.probe_tier_corr (fresh-seed, rule-scored) — instrument=probe
      2. recompute from train artifacts — instrument=train, contaminated=True
      3. metrics.tier_acc param — instrument=param, contaminated=True
    """
    entries = []
    for r in sorted(rounds, key=lambda x: x.get("g", 0)):
        g = r.get("g", 0)
        gen_id = r.get("model", {}).get("version") if isinstance(r.get("model"), dict) else None
        gen_id = gen_id or r.get("gen_id") or f"G{g}"
        m = r.get("metrics", {})
        probe = m.get("probe_tier_corr") if isinstance(m.get("probe_tier_corr"), dict) else {}
        arts = r.get("artifacts", [])
        # train recompute per tier (also serves n for train instrument)
        train_acc: dict = {}
        train_n: dict = {}
        for t in DEFAULT_TIERS:
            sub = [a for a in arts if a.get("tier") == t]
            if sub:
                train_acc[str(t)] = round(sum(1.0 if a.get("correct") else 0.0 for a in sub) / len(sub), 3)
                train_n[str(t)] = len(sub)
        skill = m.get("tier_acc")
        slices = discover_slices([r], mode) if mode == "catxtier" else [f"tier={t}" for t in DEFAULT_TIERS]
        # legacy fallback: no tier info anywhere -> overall slice from correct_rate
        if mode == "tier" and not probe and not train_acc and not isinstance(skill, list):
            acc = m.get("probe_corr", m.get("correct_rate"))
            if acc is not None:
                entries.append({
                    "gen": gen_id, "g": g, "slice": "overall",
                    "est": round(float(acc), 3), "n": ASSUMED_PROBE_N_PER_TIER,
                    "ci": _ci_from_acc(float(acc), ASSUMED_PROBE_N_PER_TIER),
                    "instrument": "probe-aggregate", "contaminated": False,
                    "n_assumed": True, "measured_by": "rule_v4",
                    "epistemic_class": "V",
                })
            continue
        for s in slices:
            tier_str = s.split("=")[-1] if s.startswith("tier=") else None
            if tier_str in probe:
                acc = float(probe[tier_str])
                n = ASSUMED_PROBE_N_PER_TIER
                entries.append({
                    "gen": gen_id, "g": g, "slice": s,
                    "est": round(acc, 3), "n": n,
                    "ci": _ci_from_acc(acc, n),
                    "instrument": "probe", "contaminated": False,
                    "n_assumed": True, "measured_by": "rule_v4",
                    "epistemic_class": "V",
                })
            elif tier_str in train_acc:
                acc = train_acc[tier_str]
                n = train_n[tier_str]
                entries.append({
                    "gen": gen_id, "g": g, "slice": s,
                    "est": acc, "n": n,
                    "ci": _ci_from_acc(acc, n),
                    "instrument": "train", "contaminated": True,
                    "n_assumed": False, "measured_by": "rule_v4",
                    "epistemic_class": "V",
                })
            elif tier_str is not None and isinstance(skill, list) and int(tier_str) < len(skill):
                acc = float(skill[int(tier_str)])
                entries.append({
                    "gen": gen_id, "g": g, "slice": s,
                    "est": round(acc, 3), "n": 0,
                    "ci": [0.0, 1.0],
                    "instrument": "param", "contaminated": True,
                    "n_assumed": True, "measured_by": "skill-param",
                    "epistemic_class": "V",
                })
            elif mode == "catxtier":
                # recompute catxtier cell from artifacts when possible
                sub = [a for a in arts if slice_key_for_artifact(a, "catxtier") == s]
                if sub:
                    acc = round(sum(1.0 if a.get("correct") else 0.0 for a in sub) / len(sub), 3)
                    entries.append({
                        "gen": gen_id, "g": g, "slice": s,
                        "est": acc, "n": len(sub),
                        "ci": _ci_from_acc(acc, len(sub)),
                        "instrument": "train", "contaminated": True,
                        "n_assumed": False, "measured_by": "rule_v4",
                        "epistemic_class": "V",
                    })
    return entries


# ---------------------------------------------------------------------------
# M matrix (importable mass)
# ---------------------------------------------------------------------------

def _is_quarantined(a: dict) -> bool:
    return bool(a.get("_misc") or a.get("quarantined") or a.get("quarantine"))


def build_M(rounds: list, mode: str = "tier") -> list:
    """Importable mass per (gen, slice) from kept sets.

    importable_mass = kept & correct & NOT quarantined.
    quarantined     = kept & _misc (coordinated-error class).
    kept_total      = kept count on slice (supply denominator).
    """
    entries = []
    for r in sorted(rounds, key=lambda x: x.get("g", 0)):
        g = r.get("g", 0)
        gen_id = r.get("model", {}).get("version") if isinstance(r.get("model"), dict) else None
        gen_id = gen_id or r.get("gen_id") or f"G{g}"
        kid = set(r.get("kept_ids", []))
        kept = [a for a in r.get("artifacts", []) if a.get("id") in kid]
        slices = discover_slices([r], mode) if mode == "catxtier" else [f"tier={t}" for t in DEFAULT_TIERS]
        if mode == "tier" and not any(a.get("tier") in (0, 1, 2) for a in r.get("artifacts", [])):
            # legacy: single overall cell
            imp = sum(1 for a in kept if a.get("correct") and not _is_quarantined(a))
            entries.append({"gen": gen_id, "g": g, "slice": "overall",
                            "importable_mass": imp,
                            "quarantined": sum(1 for a in kept if _is_quarantined(a)),
                            "kept_total": len(kept)})
            continue
        for s in slices:
            if s.startswith("tier="):
                t = int(s.split("=")[1])
                sub = [a for a in kept if a.get("tier") == t]
            else:
                sub = [a for a in kept if slice_key_for_artifact(a, "catxtier") == s]
            entries.append({
                "gen": gen_id, "g": g, "slice": s,
                "importable_mass": sum(1 for a in sub if a.get("correct") and not _is_quarantined(a)),
                "quarantined": sum(1 for a in sub if _is_quarantined(a)),
                "kept_total": len(sub),
            })
    return entries


# ---------------------------------------------------------------------------
# Frontier, regret, NDS, dormant census
# ---------------------------------------------------------------------------

def _intervals_overlap(ci_a: list, ci_b: list) -> bool:
    return not (ci_a[0] > ci_b[1] or ci_b[0] > ci_a[1])


def benjamini_hochberg(pvals: list, fdr: float = 0.05) -> list:
    """BH step-up selection over a family of p-values.

    Ported from the Nemotron-3 session contribution (its flywheel_ledger.py);
    per-comparison flags, True = significant after correction. Used to gate
    frontier flips across the S×T family (CFL roadmap hardening item).
    """
    if not pvals:
        return []
    indexed = sorted(((p, i) for i, p in enumerate(pvals)))
    m = len(pvals)
    sig = [False] * m
    for rank, (p, idx) in enumerate(indexed, 1):
        if p <= (rank / m) * fdr:
            sig[idx] = True
    return sig


def _flip_pvalue(est_c: float, n_c: int, est_h: float, n_h: int) -> float:
    """One-sided normal-approx p-value for challenger > holder.

    Unpooled SE from the two point estimates; degenerate (zero-variance or
    missing-n) cases return 1.0 (never significant). Approximate by
    construction — documented, not hidden.
    """
    try:
        if not n_c or not n_h:
            return 1.0
        var = est_c * (1 - est_c) / n_c + est_h * (1 - est_h) / n_h
        if var <= 0:
            return 1.0 if est_c <= est_h else 0.0
        import math
        z = (est_c - est_h) / math.sqrt(var)
        return round(0.5 * math.erfc(z / math.sqrt(2)), 6)
    except Exception:
        return 1.0


def build_frontier(C: list, j_class: bool = False, fdr=None) -> list:
    """Significance-gated frontier per slice.

    Holder flips only on non-overlapping Wilson intervals (challenger
    lower > holder upper). Point-estimate wins inside overlap mark the
    cell contested=True without changing the holder.

    fdr (e.g. 0.05, default None = legacy behavior): additionally require
    each flip to survive Benjamini-Hochberg correction over the candidate
    flips in this call. Rejected flips are treated like overlap ties
    (contested, holder retained).
    """
    by_slice: dict = {}
    for e in C:
        if e.get("epistemic_class") == "J" and not j_class:
            continue
        by_slice.setdefault(e["slice"], []).append(e)
    allowed = None
    if fdr is not None:
        # collect every candidate flip (challenger est above current best
        # with non-overlapping CI) across the family, then BH-gate as one set
        cands, keys = [], []
        seen_best: dict = {}
        for s in sorted(by_slice):
            rows = sorted(by_slice[s], key=lambda e: e.get("g", 0))
            best = rows[0]
            for r in rows[1:]:
                if r["est"] > best["est"] and not _intervals_overlap(r["ci"], best["ci"]):
                    cands.append(_flip_pvalue(r["est"], r.get("n", 0), best["est"], best.get("n", 0)))
                    keys.append((s, r.get("g", 0)))
                    best = r
        sig = benjamini_hochberg(cands, fdr)
        allowed = {k for k, ok in zip(keys, sig) if ok}
    frontier = []
    for s in sorted(by_slice):
        rows = sorted(by_slice[s], key=lambda e: e.get("g", 0))
        holder = rows[0]
        contested_any = False
        regrets: dict = {}
        for r in rows:
            flip_ok = r["est"] > holder["est"] and not _intervals_overlap(r["ci"], holder["ci"])
            if flip_ok and (allowed is None or (s, r.get("g", 0)) in allowed):
                holder = r
                contested = False
            elif r["est"] > holder["est"]:
                contested_any = True
                contested = True
            else:
                contested = False
            regrets[r.get("g", 0)] = round(holder["est"] - r["est"], 3)
        cur = rows[-1]
        regret_of_current = round(holder["est"] - cur["est"], 3)
        if holder["gen"] == cur["gen"]:
            status = "held"
        elif cur["est"] > holder["est"]:
            # point estimate above holder but inside Wilson overlap:
            # tie, not a trailing slice (avoids NDS=1 on flat noisy lines)
            status = "contested"
        else:
            status = "trailing"
        frontier.append({
            "slice": s,
            "holder": holder["gen"],
            "holder_g": holder.get("g", 0),
            "holder_est": holder["est"],
            "holder_ci": holder["ci"],
            "current_gen": cur["gen"],
            "current_est": cur["est"],
            "regret_of_current": regret_of_current,
            "status": status,
            "contested": contested_any,
            "n_gens": len(rows),
        })
    return frontier


def compute_nds(frontier: list) -> dict:
    """Non-dominated share: fraction of slices decisively trailing.

    Counts status=="trailing" (holder point estimate above current AND
    gated). "contested" (current point at/above holder inside overlap)
    does NOT count — it is a tie, preventing NDS=1 on flat noisy lines
    where n=16 Wilson intervals are wide by design.
    """
    if not frontier:
        return {"nds": 0.0, "n_slices": 0, "n_trailing": 0}
    trailing = sum(1 for f in frontier if f.get("status") == "trailing")
    return {"nds": round(trailing / len(frontier), 3),
            "n_slices": len(frontier), "n_trailing": trailing}


def dormant_census(frontier: list, M: list) -> list:
    """Slices where holder exists but holder's importable mass is zero."""
    m_by = {(e["gen"], e["slice"]): e for e in M}
    out = []
    for f in frontier:
        key = (f["holder"], f["slice"])
        m = m_by.get(key, {"importable_mass": 0, "kept_total": 0, "quarantined": 0})
        if m["importable_mass"] == 0:
            out.append({"slice": f["slice"], "holder": f["holder"],
                        "regret_of_current": f["regret_of_current"],
                        "kept_total": m["kept_total"],
                        "quarantined": m["quarantined"],
                        "harvest_path": "bank-regenerate-or-adapter"})
        else:
            out.append({"slice": f["slice"], "holder": f["holder"],
                        "regret_of_current": f["regret_of_current"],
                        "importable_mass": m["importable_mass"],
                        "harvest_path": "archive-import"})
    return out


def harvest_path_for(f: dict, m_holder: dict, dose_cap: float = 0.25) -> str:
    """Per-slice harvest routing, in priority order (GLM §6c)."""
    if m_holder.get("importable_mass", 0) > 0:
        return "archive-import"
    if f.get("regret_of_current", 0) <= 0.02:
        return "accept-regret"
    # dormant and regretted: procedural bank covers tier slices in this repo
    if f["slice"].startswith("tier="):
        return "bank-regenerate-or-adapter"
    return "adapter-or-accept"


# ---------------------------------------------------------------------------
# Consumers (upgrades of the four frozen mechanisms)
# ---------------------------------------------------------------------------

def deficit_weights(tier_acc: list) -> list:
    """Capability-conditioned deficit weights w_t = (1-acc)/sum. Cf. pkg13."""
    den = sum(1.0 - a for a in tier_acc) or 1.0
    return [round((1.0 - a) / den, 3) for a in tier_acc]


def regret_weights(regrets: dict) -> dict:
    """Graded regret version of the binary forgotten term (GLM §6a).

    U(a) = w_r*R(slice(a)) + w_q*final/100 + w_n*nov — this returns the
    normalized w over slices; the caller multiplies into its utility.
    """
    tot = sum(max(0.0, v) for v in regrets.values()) or 1.0
    return {k: round(max(0.0, v) / tot, 3) for k, v in sorted(regrets.items())}


def pair_coverage(c_cur: dict, c_other: dict, c_lineage_best: dict) -> float:
    """Per-slice complementarity: fraction of lineage frontier jointly covered.

    C_pair(t,tau) = sum_i max(c_t(i),c_tau(i)) / sum_i max_tau' c_tau'(i).
    Merge iff above gate (frozen default 0.5).
    """
    num = sum(max(c_cur.get(s, 0), c_other.get(s, 0)) for s in c_lineage_best)
    den = sum(c_lineage_best.values()) or 1.0
    return round(num / den, 3)


def aggregate_understatement(rounds: list, frontier: list) -> dict:
    """Quantify 'aggregate metrics understate past-generation value'.

    Compares aggregate delta (final-initial probe_corr/correct_rate) against
    NDS + max regret. Flags runs where the aggregate is flat-or-up while
    trailing slices persist — the exact case a scalar ranking hides.
    """
    ms = [r.get("metrics", {}) for r in sorted(rounds, key=lambda x: x.get("g", 0))]
    agg_key = "probe_corr" if any("probe_corr" in m for m in ms) else "correct_rate"
    agg = [m.get(agg_key) for m in ms if m.get(agg_key) is not None]
    d_agg = round(agg[-1] - agg[0], 3) if len(agg) >= 2 else 0.0
    nds = compute_nds(frontier)
    max_regret = max([f["regret_of_current"] for f in frontier] or [0.0])
    mean_regret = round(sum(f["regret_of_current"] for f in frontier) / len(frontier), 3) if frontier else 0.0
    return {"agg_key": agg_key, "agg_delta": d_agg,
            "nds": nds["nds"], "max_regret": round(max_regret, 3),
            "mean_regret": mean_regret,
            "understates": bool(abs(d_agg) < 0.05 and (nds["nds"] > 0 or max_regret >= 0.1))}


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_ledger(rounds: list, run_id: str = "run",
                  mode: str = "tier", dose_cap: float = 0.25, fdr=None,
                  stack: dict | None = None) -> dict:
    """Assemble a full capfront-ledger/v1 document for one run (combo/arm).

    stack: optional execution provenance, e.g. {"device": "cuda:0", "dtype": "float16",
    "dose_epochs": 5}. Absent stack is stamped stack_assumed (same discipline as
    n_assumed): unknown, not default-cpu. WQ6.
    """
    C = build_C(rounds, mode)
    M = build_M(rounds, mode)
    frontier = build_frontier(C, fdr=fdr)
    nds = compute_nds(frontier)
    dorm = dormant_census(frontier, M)
    m_by = {(e["gen"], e["slice"]): e for e in M}
    enriched = []
    for f, d in zip(sorted(frontier, key=lambda x: x["slice"]),
                    sorted(dorm, key=lambda x: x["slice"])):
        mh = m_by.get((f["holder"], f["slice"]), {})
        path = harvest_path_for(f, mh, dose_cap)
        enriched.append({**f, "harvest_path": path,
                         "dose_cap": dose_cap,
                         "holder_importable_mass": mh.get("importable_mass", 0)})
    under = aggregate_understatement(rounds, frontier)
    return {"schema": SCHEMA, "run_id": run_id,
            "slice_space": {"axes": ["tier"] if mode == "tier" else ["category", "tier"],
                            "mode": mode,
                            "n": len(frontier)},
            "generations": [{"id": r.get("model", {}).get("version", f"G{r.get('g', i)}")
                             if isinstance(r.get("model"), dict) else f"G{r.get('g', i)}",
                             "g": r.get("g", i)} for i, r in
                            enumerate(sorted(rounds, key=lambda x: x.get("g", 0)))],
            "C": C, "M": M, "frontier": enriched,
            "nds": nds, "understatement": under,
            "provenance": {"c_source_priority": ["probe_tier_corr", "train-recompute", "tier_acc-param"],
                            "m_source": "kept_ids x artifacts (minus _misc quarantine)",
                            "stack": dict(stack) if stack else {"device": "unknown", "dtype": "unknown",
                                                                "stack_assumed": True},
                            "gating": ("wilson-nonoverlap-95pct" if fdr is None
                                        else f"wilson-nonoverlap-95pct+fdr-{fdr}"),
                            "epistemic": "V-only by default"}}


def ledger_to_jsonable(doc: dict) -> dict:
    return json.loads(json.dumps(doc, sort_keys=True, default=str))

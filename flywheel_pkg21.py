"""
Package 21 — Per-slice complementarity gate vs scalar gate vs single parent (frozen platform)
===============================================================================================
Thread-C/pkg1 nulls came from same-lineage parents (compl <= 0.25: nothing to
merge). This package manufactures GENUINE divergence the honest way: specialist
branches with disjoint training tiers, so complementarity is real and the gates
have something to decide.
Branches (G1-G3 from shared G0; QUOTA selection 9+9 per branch — specialization
must span selection, not just pools (pools-only was tried: identical profiles)):
  E-branch: keeps easy+med (pools exclude tier 2) -> hard forgets
  H-branch: keeps med+hard (pools exclude tier 0) -> easy forgets
At G4, arms diverge (matched 36-pools; complementarity measured on branch kept):
  single     : best parent by overall kept-correct, continue full pools (control)
  scalar     : merge top-2-quality parents iff scalar jaccard-dist > 0.5
               (frozen rule), else single-best; log decision
  slicemerge : merge iff pair_coverage gain = C_pair - max(single) > 0.05
               (first parametrization; capability_ledger.pair_coverage),
               else single-best; log decision
G4-G7 continuation single-parent from G4 model, full recency pools.
C dicts for pair_coverage: per-tier kept-correct rates over last 2 branch
rounds; lineage-best = per-tier max. Metrics: per-slice deltas (merged vs
single at G7), overall, probe(-hard), compl values, gate decisions.
Seeds 0/1500/3000. 3 arms x 3 seeds x 8 rounds.
Temp .85, blind gated097, v4 scorer, fresh-seed probe, misc 0.

Usage: python flywheel_pkg21.py
Out: pkg21_merge.json
"""
from __future__ import annotations
import copy
import json
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness4 as h4
import flywheel_pkg2 as p2
import flywheel_pkg9 as p9
import flywheel_threadC as tC
import capability_ledger as cl

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
SCALAR_GATE = 0.5
GAIN_GATE = 0.05  # first parametrization for C_pair margin


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def tier_corr(arts):
    out = {}
    for t in (0, 1, 2):
        sub = [a for a in arts if a["tier"] == t]
        out[str(t)] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else None
    return out


def branch_pool(kept_hist, allowed):
    src = [a for h in kept_hist[-3:] for a in h if a["tier"] in allowed]
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def full_pool(kept_hist):
    src = [a for h in kept_hist[-3:] for a in h]
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def kept_tier_correct_rate(kept_hist, tier):
    sub = [a for h in kept_hist[-2:] for a in h if a["tier"] == tier]
    return round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else 0.0


def run_seed(seed):
    tag = f"specxseed{seed}"
    sm0 = base.make_sm0()
    sm0.version = f"{tag}-G0"
    assert sm0.params["tier_acc"] == [0.55, 0.55, 0.55]
    branches = {}
    rounds_log = []
    prev_corr, prev_bias = None, None
    # G0 shared
    gs, js = BASE_SEED + seed, BASE_SEED + seed + 11
    sm0.params["temperature"] = 0.85
    arts = p9.gen_batch(sm0, p9.BANK, 0, NPP, gs, "R0-")
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a.update({"judge_version": None, "judge_score": None,
                  "final_score": a["rule_score"], "eval_mix": "rule-only",
                  "judge_kind": None, "alpha_rule": None})
    kept0 = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
    kid = {a["id"] for a in kept0}
    for a in arts:
        a["kept"], a["phase"], a["combo"] = a["id"] in kid, "branch", tag
    m0 = h1.compute_round_metrics(arts, kept0)
    m0["tier_corr"] = tier_corr(arts)
    rounds_log.append({"g": 0, "branch": "shared", "metrics": m0, "model": sm0.to_dict(),
                       "kept_ids": sorted(kid), "artifacts": arts})
    for br, allowed in (("E", {0, 1}), ("H", {1, 2})):
        pool = [a for a in kept0 if a["tier"] in allowed][:36] or list(kept0)[:36]
        nxt = base.train_next_sm(f"{tag}-{br}-G1", [sm0], pool, [0],
                                 temp_override=0.85, lesson=f"[branch|{br}]")
        branches[br] = {"sm": nxt, "hist": [kept0], "models": [sm0, nxt]}
    # G1-G3 branch divergence
    for g in range(1, 4):
        for br, allowed in (("E", {0, 1}), ("H", {1, 2})):
            st = branches[br]
            sm = st["sm"]
            gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
            sm.params["temperature"] = 0.85
            arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{br}-")
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
            # Branch DIVERGENCE lives here (not just pools): quota selection
            # forces E onto easy+med and H onto med+hard. Plain top-k would
            # keep identical easy+med sets in both branches (v1 null rerun).
            kept = []
            for t in sorted(allowed):
                kept.extend(sorted([a for a in arts if a["tier"] == t],
                                   key=lambda a: a["final_score"], reverse=True)[:9])
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "branch", tag
            m = h1.compute_round_metrics(arts, kept)
            m["tier_corr"] = tier_corr(arts)
            m["tier_acc"] = list(sm.params["tier_acc"])
            st["hist"].append(kept)
            pool = branch_pool(st["hist"], allowed)
            nxt = base.train_next_sm(f"{tag}-{br}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[branch|{br}]")
            rounds_log.append({"g": g, "branch": br, "metrics": m, "model": sm.to_dict(),
                               "kept_ids": sorted(kid), "artifacts": arts})
            st["sm"] = nxt
            st["models"].append(nxt)
            prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
            print(f"{tag} {br} G{g}: acc={m['tier_acc']} keptshare="
                  f"{ {t: sum(1 for a in kept if a['tier'] == t) for t in (0,1,2)} }", flush=True)
    # complementarity at fork (branch G3 kept pid sets + kept-correct tiers)
    # complementarity at fork. cbest spans the FULL branch history (G0-G3, both
    # branches) — never just the pair under test, else C_pair is 1.0 by
    # construction (v1 null post-mortem). Gain = pair coverage minus best single.
    def cell_rates(kept):
        out = {}
        for t in (0, 1, 2):
            sub = [a for a in kept if a["tier"] == t]
            out[str(t)] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else 0.0
        return out
    lineage_cells = [cell_rates(kept0)]
    for br in ("E", "H"):
        for h in branches[br]["hist"]:
            lineage_cells.append(cell_rates(h))
    cbest = {s: max(c[s] for c in lineage_cells) for s in ("0", "1", "2")}
    denom = sum(cbest.values()) or 1.0
    px = {a["problem_id"] for h in branches["E"]["hist"][-2:] for a in h}
    pe = {a["problem_id"] for h in branches["H"]["hist"][-2:] for a in h}
    scalar_compl = tC._jaccard(px, pe)
    cE = {str(t): kept_tier_correct_rate(branches["E"]["hist"], t) for t in (0, 1, 2)}
    cH = {str(t): kept_tier_correct_rate(branches["H"]["hist"], t) for t in (0, 1, 2)}
    cp = cl.pair_coverage(cE, cH, cbest)
    sing_cov = max(sum(cE.values()) / denom, sum(cH.values()) / denom)
    gain = round(cp - sing_cov, 3)
    print(f"{tag} FORK compl: scalar={scalar_compl} C_pair={cp} gain={gain}", flush=True)
    out = []
    for arm in ["single", "scalar", "slicemerge"]:
        st = copy.deepcopy({"E": branches["E"], "H": branches["H"]})
        models = {"E": st["E"]["sm"], "H": st["H"]["sm"]}
        qE = mean(1.0 if a["correct"] else 0.0
                  for h in st["E"]["hist"][-2:] for a in h)
        qH = mean(1.0 if a["correct"] else 0.0
                  for h in st["H"]["hist"][-2:] for a in h)
        best_br = "E" if qE >= qH else "H"
        if arm == "single":
            parents, how = [models[best_br]], "best-single"
        elif arm == "scalar":
            parents, how = ([models["E"], models["H"]], "merged") \
                if scalar_compl > SCALAR_GATE else ([models[best_br]], "single-fallback")
        else:
            parents, how = ([models["E"], models["H"]], "merged") \
                if gain > GAIN_GATE else ([models[best_br]], "single-fallback")
        atag = f"{arm}xseed{seed}"
        if len(parents) == 1:
            sm = base.train_next_sm(f"{atag}-G4", parents,
                                    branch_pool(st[best_br]["hist"], {0, 1, 2}),
                                    [3], temp_override=0.85, lesson=f"[merge|{arm}:{how}]")
        else:
            pool = []
            for h in st["E"]["hist"][-2:] + st["H"]["hist"][-2:]:
                pool.extend(h)
            seen, poolu = set(), []
            for a in sorted(pool, key=lambda a: a["final_score"], reverse=True):
                if a["id"] not in seen:
                    seen.add(a["id"])
                    poolu.append(a)
                if len(poolu) >= 36:
                    break
            sm = tC.merge_train(f"{atag}-G4", parents, poolu, [2, 3], lesson=f"[merge|{arm}:{how}]")
            sm.params["temperature"] = 0.85
        kept_hist = [h for h in st[best_br]["hist"]] if arm == "single" \
            else [h for h in st["E"]["hist"]] + [h for h in st["H"]["hist"]]
        rounds, pc, pb = [], None, None
        for g in range(4, 8):
            gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
            sm.params["temperature"] = 0.85
            arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{arm}-")
            alpha = 0.8 if (pc is not None and (pc < 0.97 or abs(pb or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
            kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "merge", atag
            m = h1.compute_round_metrics(arts, kept)
            m["tier_corr"] = tier_corr(arts)
            m["tier_acc"] = list(sm.params["tier_acc"])
            kept_hist.append(kept)
            pool = branch_pool(kept_hist, {0, 1, 2})
            nxt = base.train_next_sm(f"{atag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[merge|{arm}]")
            rounds.append({"g": g, "arm": arm, "how": how if g == 4 else "continue",
                           "metrics": m, "model": sm.to_dict(), "kept_ids": sorted(kid),
                           "artifacts": arts})
            sm = nxt
            pc, pb = m["judge_corr"], m["leniency_bias"]
            print(f"{atag} G{g}: tiers={m['tier_corr']} acc={m['tier_acc']}", flush=True)
        out.append({"combo": atag, "arm": arm, "seed": seed, "how": how,
                    "scalar_compl": scalar_compl, "pair_gain": gain, "rounds": rounds})
    return {"branch_log": rounds_log,
            "fork": {"scalar_compl": scalar_compl, "pair_coverage": cp, "gain": gain},
            "combos": out}


def main():
    all_out, forks = [], []
    for seed in SEEDS:
        r = run_seed(seed)
        forks.append({"seed": seed, **r["fork"]})
        all_out.extend(r["combos"])
    with open(OUT / "pkg21_merge.json", "w") as f:
        json.dump({"block": "merge", "forks": forks, "combos": all_out}, f, indent=1)
    print("Wrote pkg21_merge.json")


if __name__ == "__main__":
    main()

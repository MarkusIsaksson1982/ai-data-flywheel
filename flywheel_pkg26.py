"""
Package 26 — Fallback hygiene: pruned vs polluted veto history (frozen platform)
=================================================================================
pkg24 residue (v1 accident + v2 slicemerge arm): fallback-to-single underperforms
pure single because G5+ training pools keep drawing on the VETOED branch's
history (invert-inflated scores rank its wrong arts high). Fix under test: on
fallback, PRUNE the vetoed branch's history from kept_hist.
Fork: pkg24-v2 verbatim (E blind on {0,1} correct; W invert on {2} wrong;
scalar~1.0 fires, gain~0 vetoes — asserted, else VOID).
Arms G4-G7 (blind, plain top-18, branch_pool):
  single    : E weights, kept_hist = E hist (reference)
  pruned    : E weights, kept_hist = E hist (== single by construction;
              expect BIT-IDENTICAL metrics — replication check)
  polluted  : E weights, kept_hist = E hist + W hist (status-quo fallback;
              expect trail — replicates pkg24 gap)
Verdict: pruned==single AND polluted<single => gap is 100% pool-history
pollution => doctrine: prune vetoed history on fallback (one-line rule).

Usage: python flywheel_pkg26.py (3 seeds)
Out: pkg26_prune.json
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness4 as h4
import flywheel_pkg9 as p9
import flywheel_threadC as tC
import capability_ledger as cl
import flywheel_pkg24 as p24

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]


def run_seed(seed):
    tag = f"prunexseed{seed}"
    sm0 = base.make_sm0()
    sm0.version = f"{tag}-G0"
    assert sm0.params["tier_acc"] == [0.55, 0.55, 0.55]
    branches = {}
    prev_corr, prev_bias = None, None
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
    for br in ("E", "W"):
        diet = p24.E_DIET if br == "E" else p24.W_DIET
        pool = [a for a in kept0 if a["tier"] in diet][:36] or list(kept0)[:36]
        nxt = base.train_next_sm(f"{tag}-{br}-G1", [sm0], pool, [0],
                                 temp_override=0.85, lesson=f"[branch|{br}]")
        branches[br] = {"sm": nxt, "hist": [kept0], "models": [sm0, nxt]}
    for g in range(1, 4):
        for br in ("E", "W"):
            st = branches[br]
            sm = st["sm"]
            gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
            sm.params["temperature"] = 0.85
            arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{br}-")
            if br == "E":
                alpha = 0.8 if (prev_corr is not None and
                                (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
                h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
                kept = []
                for t in sorted(p24.E_DIET):
                    kept.extend(sorted([a for a in arts if a["tier"] == t],
                                       key=lambda a: a["final_score"], reverse=True)[:9])
            else:
                h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
                kept = sorted([a for a in arts if a["tier"] == 2],
                              key=lambda a: a["final_score"], reverse=True)[:18]
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "branch", tag
            st["hist"].append(kept)
            pool = p24.branch_pool(st["hist"], p24.E_DIET if br == "E" else p24.W_DIET)
            nxt = base.train_next_sm(f"{tag}-{br}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[branch|{br}]")
            st["sm"] = nxt
            st["models"].append(nxt)
            if br == "E":
                m = h1.compute_round_metrics(arts, kept)
                prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
    # fork stats (pkg24 verbatim) + VOID guards
    lineage_cells = [p24.cell_rates(kept0)]
    for br in ("E", "W"):
        for h in branches[br]["hist"]:
            lineage_cells.append(p24.cell_rates(h))
    cbest = {s: max(c[s] for c in lineage_cells) for s in ("0", "1", "2")}
    denom = sum(cbest.values()) or 1.0
    px = {a["problem_id"] for h in branches["E"]["hist"][-2:] for a in h}
    pe = {a["problem_id"] for h in branches["W"]["hist"][-2:] for a in h}
    scalar_compl = tC._jaccard(px, pe)
    cE = {str(t): p24.kept_tier_correct_rate(branches["E"]["hist"], t) for t in (0, 1, 2)}
    cW = {str(t): p24.kept_tier_correct_rate(branches["W"]["hist"], t) for t in (0, 1, 2)}
    cp = cl.pair_coverage(cE, cW, cbest)
    sing_cov = max(sum(cE.values()) / denom, sum(cW.values()) / denom)
    gain = round(cp - sing_cov, 3)
    print(f"{tag} FORK scalar={scalar_compl} gain={gain}", flush=True)
    assert scalar_compl > p24.SCALAR_GATE and gain <= p24.GAIN_GATE, (scalar_compl, gain)
    out = []
    for arm in ["single", "pruned", "polluted"]:
        st = copy.deepcopy({"E": branches["E"], "W": branches["W"]})
        sm = st["E"]["sm"]
        pool1 = p24.branch_pool(st["E"]["hist"], {0, 1, 2})
        atag = f"{arm}xseed{seed}"
        sm = base.train_next_sm(f"{atag}-G4", [sm], pool1, [3],
                                temp_override=0.85, lesson=f"[prune|{arm}]")
        kept_hist = [h for h in st["E"]["hist"]] if arm in ("single", "pruned") \
            else [h for h in st["E"]["hist"]] + [h for h in st["W"]["hist"]]
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
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "prune", atag
            m = h1.compute_round_metrics(arts, kept)
            m["tier_corr"] = p24.tier_corr(arts)
            m["tier_acc"] = list(sm.params["tier_acc"])
            kept_hist.append(kept)
            pool = p24.branch_pool(kept_hist, {0, 1, 2})
            wshare = round(mean(1.0 if "-W-" in a["id"] else 0.0 for a in pool), 3) if pool else 0.0
            m["pool_Wshare"] = wshare
            nxt = base.train_next_sm(f"{atag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[prune|{arm}]")
            rounds.append({"g": g, "arm": arm, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
            sm = nxt
            pc, pb = m["judge_corr"], m["leniency_bias"]
            print(f"{atag} G{g}: med={m['tier_corr']['1']} Ws={wshare}", flush=True)
        out.append({"combo": atag, "arm": arm, "seed": seed,
                    "scalar_compl": scalar_compl, "pair_gain": gain, "rounds": rounds})
    return {"combos": out}


def main():
    all_out = []
    for seed in SEEDS:
        all_out.extend(run_seed(seed)["combos"])
    with open(OUT / "pkg26_prune.json", "w") as f:
        json.dump({"block": "prune", "combos": all_out}, f, indent=1)
    print("Wrote pkg26_prune.json")


if __name__ == "__main__":
    main()

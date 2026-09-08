"""
Package 12 — Pool quotas under active scarcity (frozen platform)
============================================================================
QUESTION (pkg11 follow-up): does pool-level quota rescue survive when pool
slots themselves go scarce — simultaneous k-cut selection + forgetting?
2x2 design (matched budgets everywhere):
  scarcity: selection kept 12/round (was 18); pool cap 24 over a 3-round window
            (36 candidates -> cut binds); all arms identical budgets.
  arms: A neither  (top-12 sel, top-24 pool)
        B pool    (top-12 sel, top-8/tier pool)
        C sel     (quota {4,4,4} sel, top-24 pool)
        D both    (quota {4,4,4} sel, top-8/tier pool)
Prediction from pkg11: B and D recover (pool delivers hard practice), C fails
like pkg11-B (pool re-starves), A stays floored. Critical contrast is B vs C
(pool quota vs selection quota under scarcity).
PREFIX (per seed): plain top-18, G0-G5 (replicates pkg10/11 floor; guard hard
acc <= 0.35 AND hard corr <= 0.25). FORK G6-G9 under the scarcity regime above.
Recovery = hard acc >= 0.60. Pool tier makeup logged per round (not post-hoc).

Usage: python flywheel_pkg12.py --block s0|s1500|s3000|all
Out: pkg12_scarce_{block}.json (all -> per-seed files)
"""
from __future__ import annotations
import argparse
import copy
import json
import random
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness4 as h4
import flywheel_pkg2 as p2
import flywheel_pkg9 as p9

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
SEL_TOTAL = 12
SEL_QUOTA = {0: 4, 1: 4, 2: 4}
POOL_CAP = 24
POOL_QUOTA = {0: 8, 1: 8, 2: 8}


def select_for(arts, which):
    if which in ("A", "B"):
        return sorted(arts, key=lambda a: a["final_score"], reverse=True)[:SEL_TOTAL]
    out = []
    for t, k in SEL_QUOTA.items():
        out.extend(sorted([a for a in arts if a["tier"] == t],
                          key=lambda a: a["final_score"], reverse=True)[:k])
    return out


def pool_for(which, kept_hist):
    src = [a for h in kept_hist[-3:] for a in h]
    if which in ("B", "D"):
        out = []
        for t, k in POOL_QUOTA.items():
            out.extend(sorted([a for a in src if a["tier"] == t],
                              key=lambda a: a["final_score"], reverse=True)[:k])
        return out
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= POOL_CAP:
            break
    return out


def tier_corr(arts):
    return {str(t): round(mean(1.0 if a["correct"] else 0.0
                               for a in arts if a["tier"] == t), 3) for t in (0, 1, 2)}


def run_prefix(seed):
    tag = f"floorxseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    assert sm.params["tier_acc"] == [0.55, 0.55, 0.55]
    kept_hist, rounds_out, models = [], [], [sm]
    prev_corr, prev_bias = None, None
    for g in range(6):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-")
        if g == 0:
            for a in arts:
                a.update(h4.rule_evaluate_v4(a, "v4"))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only",
                          "judge_kind": None, "alpha_rule": None})
        else:
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "collapse", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        kept_hist.append(kept)
        pool = p9.pool_for(kept_hist)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[floor|plain18]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        models.append(nxt)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]}", flush=True)
    fin = rounds_out[5]["metrics"]
    assert fin["tier_acc"][2] <= 0.35 and fin["tier_corr"]["2"] <= 0.25, fin
    print(f"prefix s{seed} at floor; forking.")
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out}


def run_arm(which, state, seed):
    st = copy.deepcopy(state)
    tag = f"scarce-{which}xseed{seed}"
    sm = st["models"][-1]
    kept_hist = [list(h) for h in st["kept_hist"]]
    rounds_out = st["rounds_out"]
    prev_corr, prev_bias = None, None
    for g in range(6, 10):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{which}-")
        alpha = 0.8 if (prev_corr is not None and
                        (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
        h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        kept = select_for(arts, which)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "recovery", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        m["kept_tier_share"] = {str(t): sum(1 for a in kept if a["tier"] == t) for t in (0, 1, 2)}
        probe = p9.gen_batch(sm, p9.PROBE_BANK, g, 2, BASE_SEED + seed + 9000 + g * 100, f"PRB{g}-")
        for a in probe:
            a.update(h4.rule_evaluate_v4(a, "v4"))
            a["final_score"] = a["rule_score"]
        m["probe_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_tier_corr"] = tier_corr(probe)
        kept_hist.append(kept)
        pool = pool_for(which, kept_hist)
        m["pool_tier_makeup"] = {str(t): sum(1 for a in pool if a["tier"] == t) for t in (0, 1, 2)}
        m["pool_hard_corr"] = round(mean(1.0 if a["correct"] else 0.0
                                        for a in pool if a["tier"] == 2), 3) \
            if any(a["tier"] == 2 for a in pool) else None
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[scarce|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                           "artifacts": arts})
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"poolhard={m['pool_tier_makeup']['2']}@{m['pool_hard_corr']} "
              f"probehard={m['probe_tier_corr']['2']}", flush=True)
    accs = [x["metrics"]["tier_acc"][2] for x in rounds_out[6:]]
    rec = next((x["g"] for x in rounds_out[6:] if x["metrics"]["tier_acc"][2] >= 0.60), None)
    fin = rounds_out[-1]["metrics"]
    return {"combo": tag, "arm": which, "seed": seed, "recovery_round": rec,
            "hard_acc_traj": accs, "final_hard": fin["tier_corr"]["2"],
            "final_acc2": fin["tier_acc"][2], "final_probehard": fin["probe_tier_corr"]["2"],
            "rounds": rounds_out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["s0", "s1500", "s3000", "all"], default="all")
    args = ap.parse_args()
    seeds = {"s0": [0], "s1500": [1500], "s3000": [3000],
             "all": [0, 1500, 3000]}[args.block]
    for seed in seeds:
        state = run_prefix(seed)
        results = [run_arm(w, state, seed) for w in ["A", "B", "C", "D"]]
        with open(OUT / f"pkg12_scarce_s{seed}.json", "w") as f:
            json.dump({"block": f"s{seed}", "combos": results}, f, indent=1)
        print(f"Wrote pkg12_scarce_s{seed}.json")


if __name__ == "__main__":
    main()

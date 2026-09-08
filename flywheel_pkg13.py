"""
Package 13 — Capability-conditioned archive valuation U(D|M,C) (frozen platform)
===============================================================================
Thread C's scalar utility failed (pool quality -> next gain r=-0.08): it prices
items without knowing what the model currently lacks. Now the substrate exists
(live tier_acc gaps) to condition on. Test: recovery-from-floor fork (pkg11
setup), selection FIXED to plain top-18 (isolates pool valuation), pools differ:
  recency : top-36 by final from last-3 kept (frozen default; replicates pkg11-A)
  scalarU : Thread-C U = .5*final/100 + .25*novelty + .25*weak-pid-flag, top-36
            from ALL history (reuse flywheel_threadC.pool_utility verbatim)
  condU   : U(D|M,C) = .4*final/100 + .4*w_tier + .2*novelty, top-36 from ALL
            history, with deficit weights w_t = (1-acc_t)/sum(1-acc) recomputed
            from the LIVE model each round (self-tuning: weight follows risk).
novelty = 1/(1+bucket count over archive); bucket = (pid, correct, len-bin).
PREFIX (per seed): plain top-18, G0-G5 (guard: hard acc <= 0.35, hard corr <=
0.25). FORK G6-G9. Recovery = hard acc >= 0.60. Calibration: per-round mean
pool U vs next-round hard-acc gain, separately for scalarU (expect ~0, Thread C)
and condU (the claim under test).
Seeds 0/1500/3000. 9 combos x 10 rounds.

Usage: python flywheel_pkg13.py (all seeds)
Out: pkg13_value.json
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

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def cond_pool(kept_hist, tier_acc):
    """Top-36 from ALL history by U(D|M,C); returns (pool, mean_U, weights)."""
    den = sum(1.0 - a for a in tier_acc) or 1.0
    w = [(1.0 - a) / den for a in tier_acc]
    freq = Counter(_bucket(a) for h in kept_hist for a in h)
    def u(a):
        return (0.40 * a["final_score"] / 100.0 + 0.40 * w[a["tier"]] +
                0.20 * (1.0 / (1.0 + freq[_bucket(a)])))
    scored = sorted([a for h in kept_hist for a in h], key=u, reverse=True)
    seen, out = set(), []
    for a in scored:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out, (round(mean(u(a) for a in out), 3) if out else None), [round(v, 3) for v in w]


def tier_corr(arts):
    return {str(t): round(mean(1.0 if a["correct"] else 0.0
                               for a in arts if a["tier"] == t), 3) for t in (0, 1, 2)}


def run_prefix(seed, prefix_sel="plain"):
    tag = f"floor-{prefix_sel}xseed{seed}"
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
        if prefix_sel == "plain":
            kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        else:  # banked prefix: stratify so the archive contains hard data
            kept = []
            for t in (0, 1, 2):
                kept.extend(sorted([a for a in arts if a["tier"] == t],
                                   key=lambda a: a["final_score"], reverse=True)[:6])
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "collapse", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        kept_hist.append(kept)
        pool = p9.pool_for(kept_hist)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[floor|plain]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        models.append(nxt)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g}: hard={m['tier_corr']['2']} acc={m['tier_acc']}", flush=True)
    fin = rounds_out[5]["metrics"]
    if prefix_sel == "plain":
        assert fin["tier_acc"][2] <= 0.35 and fin["tier_corr"]["2"] <= 0.25, fin
        print(f"prefix s{seed} at floor; forking.")
    else:
        assert fin["tier_acc"][2] >= 0.55, fin
        print(f"prefix s{seed} banked (hard acc={fin['tier_acc'][2]}); forking.")
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out}


def run_arm(which, state, seed):
    st = copy.deepcopy(state)
    tag = f"val-{which}xseed{seed}"
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
        kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "recovery", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        kept_hist.append(kept)
        if which == "recency":
            pool = p9.pool_for(kept_hist)
            mean_u = None
        elif which == "scalarU":
            pool = tC.pool_utility(kept_hist)
            mean_u = None
        else:
            pool, mean_u, w = cond_pool(kept_hist, sm.params["tier_acc"])
            m["deficit_weights"] = w
        m["mean_pool_U"] = mean_u
        m["pool_hard"] = sum(1 for a in pool if a["tier"] == 2)
        m["pool_makeup"] = {str(r): sum(1 for a in pool if a["round"] == r)
                            for r in sorted({a["round"] for a in pool})}
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[recovery|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"poolhard={m['pool_hard']} U={mean_u}", flush=True)
    rec = next((x["g"] for x in rounds_out[6:] if x["metrics"]["tier_acc"][2] >= 0.60), None)
    fin = rounds_out[-1]["metrics"]
    return {"combo": tag, "arm": which, "seed": seed, "recovery_round": rec,
            "final_hard": fin["tier_corr"]["2"], "final_acc2": fin["tier_acc"][2],
            "rounds": rounds_out}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["starved", "banked", "all"], default="all")
    args = ap.parse_args()
    plan = []
    if args.block in ("starved", "all"):
        plan.append(("starved", "plain"))
    if args.block in ("banked", "all"):
        plan.append(("banked", "strat"))
    for name, psel in plan:
        all_out = []
        for seed in SEEDS:
            state = run_prefix(seed, psel)
            for w in ["recency", "scalarU", "condU"]:
                all_out.append(run_arm(w, state, seed))
        with open(OUT / f"pkg13_value_{name}.json", "w") as f:
            json.dump({"block": name, "combos": all_out}, f, indent=1)
        print(f"Wrote pkg13_value_{name}.json")


if __name__ == "__main__":
    main()

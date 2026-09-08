"""
Package 11 — Stratified recovery from the forgetting floor (frozen platform)
============================================================================
QUESTION (pkg10 follow-up): quotas preserve hard skill when applied from the
start — but do they RECOVER a skill already at the forgetting floor, or only
slow the fall while data is scarce? No new substrate; tier_acc machinery as in
pkg10 (learn own-tier, forget unpracticed toward 0.30).

PREFIX (per seed): plain top-18, G0-G5 (replicates pkg10 plain; guard: G5 hard
acc <= 0.35 AND hard corr <= 0.25). FORK (deepcopy) at G6 for G6-G9:
  A plain      : top-18 final (control — stays floored?)
  B equal      : top-6 per tier final (rescue at parity)
  C hard-heavy : quota {easy:4, med:5, hard:9} by final (dose-response: does
                 overweighting hard accelerate recovery, or dilute with worse data?)
Pools recency-36 by final (frozen; pools follow selection — isolates quota effect).
Temp .85, blind gated097, v4 scorer, fresh-seed probe bank, misc 0.
Recovery = hard acc >= 0.60 (rounds-to) + hard corr + probe-hard trajectories.

Usage: python flywheel_pkg11.py (3 seeds: prefix + 3 arms each)
Out: pkg11_recover.json
"""
from __future__ import annotations
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
QUOTAS = {"A": None, "B": {0: 6, 1: 6, 2: 6}, "C": {0: 4, 1: 5, 2: 9}}


def select_for(arts, which):
    if which == "A":
        return sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
    out = []
    for t, k in QUOTAS[which].items():
        out.extend(sorted([a for a in arts if a["tier"] == t],
                          key=lambda a: a["final_score"], reverse=True)[:k])
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
        kept = select_for(arts, "A")
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "collapse", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        kept_hist.append(kept)
        pool = p9.pool_for(kept_hist) if len(kept_hist) > 1 else list(kept)
        # NOTE: pkg10 used pool_for(kept_hist+[kept]) if kept_hist else list(kept);
        # identical content here (kept_hist already includes current kept).
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[floor|plain]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        models.append(nxt)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]}", flush=True)
    fin = rounds_out[5]["metrics"]
    assert fin["tier_acc"][2] <= 0.35 and fin["tier_corr"]["2"] <= 0.25, fin
    print(f"prefix s{seed} at floor (acc={fin['tier_acc'][2]}, hard={fin['tier_corr']['2']}); forking.")
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out}


def run_arm(which, state, seed):
    st = copy.deepcopy(state)
    tag = f"rec-{which}xseed{seed}"
    sm = st["models"][-1]  # M_6, trained at G5 end under plain
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
        pool = p9.pool_for(kept_hist)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[recovery|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                           "pool_makeup": {str(r): sum(1 for a in pool if a["round"] == r)
                                           for r in sorted({a["round"] for a in pool})},
                           "artifacts": arts})
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"probehard={m['probe_tier_corr']['2']}", flush=True)
    accs = [x["metrics"]["tier_acc"][2] for x in rounds_out[6:]]
    rec = next((x["g"] for x in rounds_out[6:] if x["metrics"]["tier_acc"][2] >= 0.60), None)
    fin = rounds_out[-1]["metrics"]
    return {"combo": tag, "arm": which, "seed": seed,
            "recovery_round": rec, "hard_acc_traj": accs,
            "final_hard": fin["tier_corr"]["2"], "final_acc2": fin["tier_acc"][2],
            "final_probehard": fin["probe_tier_corr"]["2"], "rounds": rounds_out}


def main():
    all_out = []
    for seed in SEEDS:
        state = run_prefix(seed)
        for w in ["A", "B", "C"]:
            all_out.append(run_arm(w, state, seed))
    with open(OUT / "pkg11_recover.json", "w") as f:
        json.dump({"block": "recover", "combos": all_out}, f, indent=1)
    print("Wrote pkg11_recover.json")


if __name__ == "__main__":
    main()

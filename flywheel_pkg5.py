"""
Package 5 — Recovery from compounding decay + probe stopping rule (frozen platform)
====================================================================================
FAILURE MODE (Package 4): growth=0.35 makes long chains disproportionately wrong;
verbosity proxy (+80) + heritable temp selects/amplifies them; flywheel drives
0.37->0.43 while control reaches 0.87; probe leads the decline.

A. FORK-AND-RESCUE: live prefix G0-G5 replicates pkg4 comp80 exactly per seed
   (assert-guarded: G5 main must match pkg4 within 0.01), then deepcopy-fork
   into 5 arms for G6-G9 (growth stays 0.35 — environment unchanged):
     A control : proxy80 selection + heritable temp continue (absorbing check)
     B amputate: keep only len<=2, top-18 by rule; temp clamp 0.7
     C soft-pen: score rule-12*max(0,len-2); temp fixed 0.85
     D cleandata: selection stays proxy80 (pressure lingers); training pool =
       top-36 by rule from R0-R2 only (pre-collapse data vs poisoned selection)
     E combo   : C scoring + C-scored top-36 pool from R0-R2; temp 0.85
   Training pools recency-36 ranked by arm score (B/C/E) except D/E early-data.
   Judge blind+gated097 throughout. Recovery = first G>=6 with main >=
   prefix-R1/R2-min - 0.05 AND probe >= same bar.
B. STOPPING RULE (post-hoc over pkg4_comp.json + these rescue runs, no new runs
   needed): fire at g>=2 iff (probe[g-2]-probe[g] >= 0.10) AND
   (main[g-2]-main[g] <= 0.05) — probe fell 10pts over 2 rounds while main held.
   Metrics: fire round, lead time vs later main drop (>0.15 below peak-to-date),
   checkpoint residual (main at fire-1), false positives on growth-0 runs.

Usage: python flywheel_pkg5.py --block s0|s1500|s3000|all (prefix+5 arms per seed)
Out: pkg5_{block}.json
"""
from __future__ import annotations
import argparse
import copy
import json
import math
import random
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness3 as h3
import flywheel_harness4 as h4
import flywheel_pkg2 as p2

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
LENBIN_CAP = 8  # unused here; kept for cross-file comparability
EXPECTED_G5 = {0: 0.472, 1500: 0.389, 3000: 0.417}  # pkg4 comp80 G5 main per seed


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def arm_score(which, art):
    if which == "A":
        return art["rule_score"] + 80 * len(art["cot"])
    if which == "C":
        return art["rule_score"] - 12 * max(0, len(art["cot"]) - 2)
    if which == "E":
        return art["rule_score"] - 12 * max(0, len(art["cot"]) - 2)
    if which == "D":
        return art["rule_score"] + 80 * len(art["cot"])
    raise ValueError(which)


def select_for(which, arts, kept_hist):
    if which in ("A", "D"):
        return sorted(arts, key=lambda a: arm_score(which, a), reverse=True)[:18]
    if which == "B":
        short = [a for a in arts if len(a["cot"]) <= 2] or arts  # fallback guard
        return sorted(short, key=lambda a: a["rule_score"], reverse=True)[:18]
    if which in ("C", "E"):
        return sorted(arts, key=lambda a: arm_score(which, a), reverse=True)[:18]
    raise ValueError(which)


def pool_for(which, kept_hist, g):
    if which in ("A", "B", "C"):
        hists = ([kept_hist[-3]] if len(kept_hist) >= 3 else []) + \
                ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]]
        src = [a for h in hists for a in h]
        key = (lambda a: arm_score(which, a)) if which in ("A", "C") else (lambda a: a["rule_score"])
    else:  # D, E: pre-collapse R0-R2 only
        src = [a for h in kept_hist[:3] for a in h]
        key = (lambda a: a["rule_score"]) if which == "D" else (lambda a: arm_score(which, a))
    seen, out = set(), []
    for a in sorted(src, key=key, reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def gen_probe(sm, g, seed):
    rng = random.Random(BASE_SEED + seed + 9000 + g * 100)
    arts = [base.generate_artifact(sm, p, f"PRB{g}-{i:02d}", g, rng)
            for i, p in enumerate(p2.PROBE * p2.PROBE_NPP)]
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    return arts


def len_corr(arts):
    xs = [len(a["cot"]) for a in arts]
    ys = [1.0 if a["correct"] else 0.0 for a in arts]
    mx, my = mean(xs), mean(ys)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den, 3) if den else 0.0


def run_prefix(seed):
    """G0-G5 pkg4-comp80 replica. Returns state for forking."""
    tag = f"prefixxseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["compound_growth"] = 0.35
    kept_hist, rounds_out = [], []
    prev_corr, prev_bias = None, None
    g0dist, temp = None, 0.85
    for g in range(6):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = temp
        arts = base.generate_batch(sm, g, NPP, gs)
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
        kept = sorted(arts, key=lambda a: a["rule_score"] + 80 * len(a["cot"]), reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, ("normal" if g < 6 else "x"), tag
        m = h1.compute_round_metrics(arts, kept)
        if g0dist is None:
            g0dist = h4.tmpl_dist(arts)
        kept_hist.append(kept)
        pool = pool_for("A", kept_hist, g)  # kept_hist now includes current (mirrors pkg4)
        temp = round(min(1.3, max(0.55, 0.7 + 0.15 * mean(len(a["cot"]) for a in kept))), 3)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=temp, lesson="[prefix|comp80]")
        nxt.params["compound_growth"] = 0.35
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g}: main={m['correct_rate']}", flush=True)
    assert abs(rounds_out[5]["metrics"]["correct_rate"] - EXPECTED_G5[seed]) < 0.01, \
        rounds_out[5]["metrics"]
    print(f"prefix s{seed} matches pkg4 (G5={EXPECTED_G5[seed]}). forking.")
    return {"sm": sm, "kept_hist": kept_hist, "rounds_out": rounds_out,
            "prev": (prev_corr, prev_bias), "g0dist": g0dist, "temp": temp}


def run_arm(which, state, seed):
    st = copy.deepcopy(state)
    tag = f"rescue-{which}xseed{seed}"
    sm, kept_hist = st["sm"], st["kept_hist"]
    rounds_out = st["rounds_out"]
    prev_corr, prev_bias = st["prev"]
    g0dist, temp = st["g0dist"], st["temp"]
    for g in range(6, 10):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        if which == "B":
            temp = 0.7
        elif which in ("C", "E"):
            temp = 0.85
        # A, D keep heritable temp dynamics from prefix state
        sm.params["temperature"] = temp
        arts = base.generate_batch(sm, g, NPP, gs)
        alpha = 0.8 if (prev_corr is not None and
                        (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
        h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        kept = select_for(which, arts, kept_hist)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "recovery", tag
        m = h1.compute_round_metrics(arts, kept)
        probe = gen_probe(sm, g, seed)
        probe_corr = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_corr"] = probe_corr
        m["proxy_true_gap"] = round(m["correct_rate"] - probe_corr, 3)
        m["mean_kept_len"] = round(mean(len(a["cot"]) for a in kept), 2)
        m["len_corr"] = len_corr(arts)
        m["drift_g0"] = h4.tvd(h4.tmpl_dist(arts), g0dist)
        m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        pool = pool_for(which, kept_hist + [kept], g)
        if which in ("A", "D"):
            temp = round(min(1.3, max(0.55, 0.7 + 0.15 * m["mean_kept_len"])), 3)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=temp, lesson=f"[rescue|{which}]")
        nxt.params["compound_growth"] = 0.35
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": probe_corr,
                           "pool_makeup": {str(r): sum(1 for a in pool if a["round"] == r)
                                           for r in sorted({a["round"] for a in pool})},
                           "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt
        print(f"arm {which} s{seed} G{g}: main={m['correct_rate']} probe={probe_corr} "
              f"len={m['mean_kept_len']} lencorr={m['len_corr']}", flush=True)
    base_q = min(rounds_out[1]["metrics"]["correct_rate"], rounds_out[2]["metrics"]["correct_rate"])
    rec = next((x["g"] for x in rounds_out[6:]
                if x["metrics"]["correct_rate"] >= base_q - 0.05
                and x["metrics"]["probe_corr"] >= base_q - 0.05), None)
    fin = rounds_out[9]["metrics"]
    return {"combo": tag, "arm": which, "seed": seed, "baseline_q": round(base_q, 3),
            "recovery_round": rec, "recovery_success": rec is not None,
            "cov_margin": None, "q_margin": round(fin["correct_rate"] - (base_q - 0.05), 3),
            "probe_margin": round(fin["probe_corr"] - (base_q - 0.05), 3),
            "rounds": rounds_out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["s0", "s1500", "s3000", "all"], default="all")
    args = ap.parse_args()
    seeds = {"s0": [0], "s1500": [1500], "s3000": [3000],
             "all": [0, 1500, 3000]}[args.block]
    for seed in seeds:
        state = run_prefix(seed)
        results = [run_arm(w, state, seed) for w in ["A", "B", "C", "D", "E"]]
        with open(OUT / f"pkg5_s{seed}.json", "w") as f:
            json.dump({"block": f"s{seed}", "combos": results}, f, indent=1)
        print(f"Wrote pkg5_s{seed}.json")


if __name__ == "__main__":
    main()

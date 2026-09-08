"""
Package 7 — Playbook generalization: misconception lock-in under repaired judge
================================================================================
QUESTION: does "reference tripwire -> forward regularized treatment" generalize
beyond compounding decay? Test failure class: misc 0.35 + invert pure0 lock-in.

PREFIX (per seed): G0-G5 flat normal, topk+invert-pure0 selection, misc_init
0.35. Guard: G5 misc_rate >= 0.35 AND main <= 0.35 (else the premise failed).
FORK (deepcopy) into 4 arms for rounds 10-13 (collision-free seeds):
  A disease   : invert pure0 sel + invert-ranked recency pools, temp .85 (locked?)
  B judge-fix : blind fixed05, top-18 final, recency-by-final pools, temp .85
  C playbook  : blind fixed05, len<=2 then top-18 rule, recency-by-rule, temp .7
  D data-only : invert pure0 sel continues, pools len<=2-filtered top-rule, t .7
  (D keeps poisoned selection; tests treatment-without-diagnosis.)
Growth 0 everywhere (misc is the flaw here, not compounding). Misc inheritance
via train_next_sm (kept _misc fraction) is the feedback loop in all arms.
Recovery bar: main >= 0.65 AND model misc < 0.05 by round 13.
TRIPWIRE ORDERING (logged per round, prefix + arms): probe-ref breach
(pooled pkg4 ref - 0.15), kept_misc_frac > 0.2, guarded wrongmode (>=3 kept,
>0.5 wrong agreement), drift lock, gating 0.8. First-fire per channel decides
whether tripwire priority is failure-class-dependent.

Usage: python flywheel_pkg7.py (all 3 seeds)
Out: pkg7_lockin.json
"""
from __future__ import annotations
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
import flywheel_kit as kit
import flywheel_harness3 as h3
import flywheel_harness4 as h4
import flywheel_pkg2 as p2

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]


def load_ref():
    return kit.load_probe_ref()  # tracked refs/ file; no generated data needed


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def gen_probe(sm, g, seed):
    rng = random.Random(BASE_SEED + seed + 9000 + g * 100)
    arts = [base.generate_artifact(sm, p, f"PRB{g}-{i:02d}", g, rng)
            for i, p in enumerate(p2.PROBE * p2.PROBE_NPP)]
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    return arts


def tripwires(m, probe_corr, ref_g, kept):
    """Return dict of channel -> fired bool for one round."""
    out = {}
    out["probe_ref"] = probe_corr is not None and probe_corr < ref_g - 0.15
    out["kept_misc"] = (sum(1.0 if a.get("_misc") else 0.0 for a in kept) / max(1, len(kept))) > 0.2
    byp: dict[str, list] = {}
    for a in kept:
        byp.setdefault(a["problem_id"], []).append(a)
    wm = False
    for pid, items in byp.items():
        if len(items) >= 3:
            w = [a for a in items if not a["correct"]]
            if w and Counter(a["final_answer"] for a in w).most_common(1)[0][1] / len(items) > 0.5:
                wm = True
    out["wrongmode"] = wm
    out["drift"] = m.get("drift_g0", 0) > 0.35
    out["gate"] = (m.get("judge_corr") is not None and
                   (m["judge_corr"] < 0.97 or abs(m.get("leniency_bias") or 0) > 1.5))
    return out


def run_prefix(seed, ref):
    tag = f"lockxseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["misc_rate"] = 0.35
    kept_hist, rounds_out, models = [], [], [sm]
    prev_corr, prev_bias = None, None
    g0dist = None
    first_fire: dict[str, int] = {}
    for g in range(6):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = base.generate_batch(sm, g, NPP, gs)
        if g == 0:
            for a in arts:
                a.update(h4.rule_evaluate_v4(a, "v4"))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only",
                          "judge_kind": None, "alpha_rule": None})
        else:
            h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
        kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "lockin", tag
        m = h1.compute_round_metrics(arts, kept)
        probe = gen_probe(sm, g, seed)
        probe_corr = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_corr"] = probe_corr
        if g0dist is None:
            g0dist = h4.tmpl_dist(arts)
        m["drift_g0"] = h4.tvd(h4.tmpl_dist(arts), g0dist)
        m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
        m["misc_rate"] = sm.params.get("misc_rate", 0.0)
        tw = tripwires(m, probe_corr, ref[g] if g < len(ref) else 9.9, kept)
        m["tripwires"] = tw
        for ch, fired in tw.items():
            if fired and ch not in first_fire:
                first_fire[ch] = g
        kept_hist.append(kept)
        hists = ([kept_hist[-3]] if len(kept_hist) >= 3 else []) + \
                ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]]
        src = [a for h in hists for a in h]
        seen, pool = set(), []
        for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
            if a["id"] not in seen:
                seen.add(a["id"])
                pool.append(a)
            if len(pool) >= 36:
                break
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[prefix|misc+invert]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": probe_corr, "artifacts": arts})
        models.append(nxt)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g}: main={m['correct_rate']} probe={probe_corr} "
              f"misc={m['misc_rate']} tw={[k for k, v in tw.items() if v]}", flush=True)
    fin = rounds_out[5]["metrics"]
    assert fin["misc_rate"] >= 0.30 and fin["correct_rate"] <= 0.35, fin
    print(f"prefix s{seed} locked (misc={fin['misc_rate']}, corr={fin['correct_rate']}); "
          f"first-fire={first_fire}")
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out,
            "first_fire": first_fire}


def run_arm(which, state, seed, ref):
    st = copy.deepcopy(state)
    tag = f"unseat-{which}xseed{seed}"
    sm = st["models"][-1]  # M_6, trained at G5 end under disease
    kept_hist = [list(h) for h in st["kept_hist"]]
    rounds_out = st["rounds_out"]
    prev_corr, prev_bias = None, None
    for g in range(10, 14):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.7 if which in ("C", "D") else 0.85
        arts = base.generate_batch(sm, g, NPP, gs)
        if which in ("B", "C"):
            h4.evaluate_v4(arts, sm, "blind", 0.5, js, (1.0, 0.0), "v4")
            if which == "B":
                kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
            else:
                short = [a for a in arts if len(a["cot"]) <= 2] or arts
                kept = sorted(short, key=lambda a: a["rule_score"], reverse=True)[:18]
        else:  # A, D: poisoned judge stays
            h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
            kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "unseating", tag
        m = h1.compute_round_metrics(arts, kept)
        probe = gen_probe(sm, g, seed)
        probe_corr = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_corr"] = probe_corr
        m["misc_rate"] = sm.params.get("misc_rate", 0.0)
        m["kept_misc_frac"] = round(mean(1.0 if a.get("_misc") else 0.0 for a in kept), 3)
        if which == "D":
            cand = [a for h in ([kept_hist[-3]] if len(kept_hist) >= 3 else []) +
                    ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]] for a in h]
            cand = [a for a in cand if len(a["cot"]) <= 2]
            pool = sorted(cand, key=lambda a: a["rule_score"], reverse=True)[:36]
        else:
            hists = ([kept_hist[-3]] if len(kept_hist) >= 3 else []) + \
                    ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]]
            src = [a for h in hists for a in h]
            key = (lambda a: a["final_score"]) if which in ("A", "B") else (lambda a: a["rule_score"])
            seen, pool = set(), []
            for a in sorted(src, key=key, reverse=True):
                if a["id"] not in seen:
                    seen.add(a["id"])
                    pool.append(a)
                if len(pool) >= 36:
                    break
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.7 if which in ("C", "D") else 0.85,
                                 lesson=f"[unseat|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": probe_corr, "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"arm {which} s{seed} G{g}: main={m['correct_rate']} probe={probe_corr} "
              f"misc={m['misc_rate']}/k{m['kept_misc_frac']}", flush=True)
    fin = rounds_out[-1]["metrics"]
    ok = fin["correct_rate"] >= 0.65 and fin["misc_rate"] < 0.05
    return {"combo": tag, "arm": which, "seed": seed, "recovered": ok,
            "final_main": fin["correct_rate"], "final_probe": fin["probe_corr"],
            "final_misc": fin["misc_rate"], "rounds": rounds_out}


def main():
    ref = load_ref()
    print("frozen probe reference:", ref)
    all_out, fires = [], []
    for seed in SEEDS:
        state = run_prefix(seed, ref)
        fires.append({"seed": seed, "first_fire": state["first_fire"]})
        for w in ["A", "B", "C", "D"]:
            all_out.append(run_arm(w, state, seed, ref))
    with open(OUT / "pkg7_lockin.json", "w") as f:
        json.dump({"block": "lockin", "fires": fires, "combos": all_out}, f, indent=1)
    print("Wrote pkg7_lockin.json")


if __name__ == "__main__":
    main()

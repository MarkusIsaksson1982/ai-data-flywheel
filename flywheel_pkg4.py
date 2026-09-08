"""
Package 4 — Compounding errors: wrongness coincides structurally with length
============================================================================
COMPLEXITY INCREASE: base generator gains `compound_growth` (guarded, default
0; legacy streams bit-identical): per-step accuracy decays geometrically with
step position, so LONG CHAINS ARE DISPROPORTIONATELY WRONG. Verified sign flip
on P04 (len->corr {1:.0,2:.4,3:.68} at growth 0 vs {1:.5,2:.41,3:.3} at 0.35).
A verbosity proxy now ANTI-correlates with correctness — the structural
coincidence Package 3 proved necessary. Probe set (with extra-step variants)
should be differentially sensitive: leading-indicator test included.

ARMS (matched recency-36 pools ranked by arm score; heritable temp
next=clip(0.7+0.15*keptlen); growth fixed per run, not learned; 6 rounds):
  control    : rank final, temp fixed .85, growth 0
  comp30     : growth .35, rank rule+30*len, heritable temp
  comp80     : growth .35, rank rule+80*len, heritable temp
  comp-guard : growth .35, rank proxy30+15*nov w/ cap 8 per len-bin, heritable
Judge blind+gated097 (scores only). Seeds 0/1500/3000.
Manipulation check per round: batch correlation(len(cot), correct) — must be
~0 in control, negative in comp arms.

Usage: python flywheel_pkg4.py --block all (single block, 12 combos)
Out: pkg4_comp.json
"""
from __future__ import annotations
import argparse
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
SEEDS = [0, 1500, 3000]
LENBIN_CAP = 8
GROWTH = {"control": 0.0, "comp30": 0.35, "comp80": 0.35, "comp-guard": 0.35}
WEIGHT = {"comp30": 30, "comp80": 80, "comp-guard": 30}


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def score_of(arm, art, freq=None):
    if arm == "control":
        return art["final_score"]
    s = art["rule_score"] + WEIGHT[arm] * len(art["cot"])
    if arm == "comp-guard":
        s += 15 * (1.0 / (1.0 + (freq or Counter())[_bucket(art)]))
    return s


def select_current(arts, kept_hist, arm):
    if arm in ("control", "comp30", "comp80"):
        key = (lambda a: score_of(arm, a)) if arm != "control" else (lambda a: a["final_score"])
        return sorted(arts, key=key, reverse=True)[:18]
    freq = Counter(_bucket(a) for h in kept_hist for a in h)
    ranked = sorted(arts, key=lambda a: score_of(arm, a, freq), reverse=True)
    kept, perbin = [], Counter()
    for a in ranked:
        b = min(len(a["cot"]), 5)
        if perbin[b] < LENBIN_CAP:
            kept.append(a)
            perbin[b] += 1
            freq[_bucket(a)] += 1
        if len(kept) >= 18:
            break
    return kept


def pool_for(arm, kept_hist):
    hists = ([kept_hist[-3]] if len(kept_hist) >= 3 else []) + \
            ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]]
    src = [a for h in hists for a in h]
    freq = Counter(_bucket(a) for h in kept_hist for a in h)
    key = (lambda a: score_of(arm, a, freq)) if arm != "control" else (lambda a: a["final_score"])
    seen, out = set(), []
    for a in sorted(src, key=key, reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def len_corr(arts):
    xs = [len(a["cot"]) for a in arts]
    ys = [1.0 if a["correct"] else 0.0 for a in arts]
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den, 3) if den else 0.0


def gen_probe(sm, g, seed):
    rng = random.Random(BASE_SEED + seed + 9000 + g * 100)
    arts = [base.generate_artifact(sm, p, f"PRB{g}-{i:02d}", g, rng)
            for i, p in enumerate(p2.PROBE * p2.PROBE_NPP)]
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    return arts


def run_arm(arm, seed):
    tag = f"{arm}xseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["compound_growth"] = GROWTH[arm]
    kept_hist: list = []
    sig_archive: set = set()
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    g0dist = None
    temp = 0.85
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
            alpha = None
        else:
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        kept = select_current(arts, kept_hist, arm)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "normal", tag
        sigs = [p2.path_sig(a) for a in kept]
        new_path = round(sum(1 for s in sigs if s not in sig_archive) / max(1, len(sigs)), 3)
        for s in sigs:
            sig_archive.add(s)
        m = h1.compute_round_metrics(arts, kept)
        probe = gen_probe(sm, g, seed)
        probe_corr = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_corr"] = probe_corr
        m["proxy_true_gap"] = round(m["correct_rate"] - probe_corr, 3)
        m["new_path_rate"] = new_path
        m["mean_kept_len"] = round(mean(len(a["cot"]) for a in kept), 2)
        m["len_corr"] = len_corr(arts)
        m["temp"] = temp
        if g0dist is None:
            g0dist = h4.tmpl_dist(arts)
        m["drift_g0"] = h4.tvd(h4.tmpl_dist(arts), g0dist)
        m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        pool = pool_for(arm, kept_hist + [kept]) if kept_hist else list(kept)
        if arm != "control":
            temp = round(min(1.3, max(0.55, 0.7 + 0.15 * m["mean_kept_len"])), 3)
        nxt = None
        if g < 5:
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=temp, lesson=f"[normal|{arm}]")
            nxt.params["compound_growth"] = GROWTH[arm]
        rounds_out.append({"g": g, "arm": arm, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": probe_corr,
                           "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        print(f"{tag} G{g}: main={m['correct_rate']} probe={probe_corr} len={m['mean_kept_len']} "
              f"lencorr={m['len_corr']} temp={m['temp']} newpath={new_path} drift={m['drift_g0']} a={alpha}",
              flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "rounds": rounds_out}


def main():
    combos = [(a, o) for a in ["control", "comp30", "comp80", "comp-guard"] for o in SEEDS]
    print(f"--- block comp: {len(combos)} combos ---")
    results = [run_arm(*c) for c in combos]
    with open(OUT / "pkg4_comp.json", "w") as f:
        json.dump({"block": "comp", "combos": results}, f, indent=1)
    print("Wrote pkg4_comp.json")


if __name__ == "__main__":
    main()

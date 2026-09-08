"""
Package 3 — Breaking the margin rule + tripwire timing (frozen platform)
=========================================================================
COMPLEXITY INCREASE (why this is new, not a variant): every settled result so
far rests on the ~60pt correct/wrong score gap — no proxy ever exceeded it, so
selection could never flip. This package creates (a) a generator with a genuine
fluency<->correctness tradeoff (trap_rate: rambling derails the final answer
while the format stays well-formed), (b) heritable verbosity (next temp tracks
mean kept length — Goodhart compounding across rounds), and (c) above-gap proxy
weights (+30/step: max differential ~90 > 60). It then measures whether
collapse finally appears and whether tripwires fire before quality does.

ARMS (matched 36-pools ranked by the arm's own selection score; 6 rounds):
  control : rank final_score, temp fixed 0.85, trap 0 (frozen default)
  gap12   : rank rule+12*len, temp heritable, trap 0 (below-gap, expect null)
  gap30   : rank rule+30*len, temp heritable, trap 0 (above-gap, no tradeoff)
  trap30  : rank rule+30*len, temp heritable, trap 0.6 (tradeoff bites?)
  guard30 : rank proxy30+15*novelty w/ cap 8 per len-bin, temp heritable, trap 0.6
Judge stays blind+gated097 (scores only; selection ranks are the treatment).
Heritable temp: next = clip(0.7 + 0.15*mean_kept_len, 0.55, 1.3).

TRIPWIRES TIMED per round: probe gap (main-probe > 0.15?), drift lock,
gating alpha 0.8, wrongmode share, new_path/dup_high, keptlen trend.
Probe + provenance imported from pkg2 (frozen).

Usage: python flywheel_pkg3.py --block base|trap|all
Out: pkg3_{block}.json
"""
from __future__ import annotations
import argparse
import json
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
import flywheel_pkg2 as p2  # PROBE, path_sig, probe registration (frozen)

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
LENBIN_CAP = 8
# Calibration note (learned mid-experiment): with in-pool length differentials
# of <=2 steps, even +30 cannot flip correct-short vs wrong-long (needs >=3).
# gap80/guard80 (+80/step: one extra step outweighs the whole ~60pt gap) are
# the true above-gap test.
WEIGHT = {"gap12": 12, "gap30": 30, "trap30": 30, "guard30": 30, "gap80": 80, "guard80": 80}
TRAP = {"control": 0.0, "gap12": 0.0, "gap30": 0.0, "trap30": 0.6, "guard30": 0.6,
        "gap80": 0.0, "guard80": 0.6}
HERITABLE = {"control": False, "gap12": True, "gap30": True, "trap30": True, "guard30": True,
             "gap80": True, "guard80": True}


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def score_of(arm, art, freq=None):
    if arm == "control":
        return art["final_score"]
    s = art["rule_score"] + WEIGHT[arm] * len(art["cot"])
    if arm == "guard30":
        s += 15 * (1.0 / (1.0 + (freq or Counter())[_bucket(art)]))
    return s


def select_current(arts, kept_hist, arm):
    if arm in ("control", "gap12", "gap30", "trap30", "gap80"):
        key = (lambda a: score_of(arm, a)) if arm != "control" else (lambda a: a["final_score"])
        return sorted(arts, key=key, reverse=True)[:18]
    if arm in ("guard30", "guard80"):
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
    raise ValueError(arm)


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
    sm.params["trap_rate"] = TRAP[arm]
    kept_hist: list = []
    sig_archive: set = set()
    rounds_out: list = []
    prev_corr, prev_bias, alpha_hist = None, None, []
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
        alpha_hist.append(alpha)
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
        m["temp"] = temp
        if g0dist is None:
            g0dist = h4.tmpl_dist(arts)
        m["drift_g0"] = h4.tvd(h4.tmpl_dist(arts), g0dist)
        m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        pool = pool_for(arm, kept_hist + [kept]) if kept_hist else list(kept)
        if HERITABLE[arm]:
            temp = round(min(1.3, max(0.55, 0.7 + 0.15 * m["mean_kept_len"])), 3)
        nxt = None
        if g < 5:
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=temp, lesson=f"[normal|{arm}]")
            nxt.params["trap_rate"] = TRAP[arm]  # environment property, not learned
        rounds_out.append({"g": g, "arm": arm, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid),
                           "probe_corr": probe_corr,
                           "probe_sample": [{"id": a["id"], "correct": a["correct"]} for a in probe],
                           "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        print(f"{tag} G{g}: main={m['correct_rate']} probe={probe_corr} len={m['mean_kept_len']} "
              f"temp={m['temp']} newpath={new_path} drift={m['drift_g0']} a={alpha}", flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "alphas": alpha_hist, "rounds": rounds_out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["base", "trap", "break", "all"], default="all")
    args = ap.parse_args()
    blocks = {"base": ["control", "gap12", "gap30"], "trap": ["trap30", "guard30"],
              "break": ["gap80", "guard80"]}
    if args.block != "all":
        blocks = {args.block: blocks[args.block]}
    for name, arms in blocks.items():
        combos = [(a, o) for a in arms for o in SEEDS]
        print(f"--- block {name}: {len(combos)} combos ---")
        results = [run_arm(*c) for c in combos]
        with open(OUT / f"pkg3_{name}.json", "w") as f:
            json.dump({"block": name, "combos": results}, f, indent=1)
        print(f"Wrote pkg3_{name}.json")


if __name__ == "__main__":
    main()

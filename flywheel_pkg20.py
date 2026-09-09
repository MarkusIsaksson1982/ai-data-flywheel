"""
Package 20 — Regret-weighted vs binary-forgotten import (frozen platform)
============================================================================
First policy experiment the ledger was built for (roadmap pkg20). Question: does
a graded regret signal beat the binary forgotten-term for archive import, in a
regime where NDS is material (tier forgetting)?
Arms (selection FIXED plain top-18 — isolates pool policy; pools capped 36):
  recency : top-36 by final from last-3 kept (frozen default)
  binary  : Thread-C utility (0.5*final/100 + 0.25*novelty + 0.25*weak-flag)
            top-36 from ALL history (tC.pool_utility verbatim)
  regret  : U = 0.5*R_norm + 0.3*final/100 + 0.2*nov, top-36 from ALL history,
            with R from live ledger rebuild each round (capability_ledger.
            build_ledger -> frontier regret_of_current -> regret_weights).
            Slice key "tier=N"; weights renormalized per round (self-tuning).
PREFIX (per seed): plain top-18 G0-G5 (guard: hard acc <= 0.35, hard corr <=
0.25). FORK G6-G9. Recovery = hard acc >= 0.60. H-RAT retrospective: per round
log R (regret), A (importable mass>0), realized next-round hard gain as the
empirical T proxy — tests whether R*A predicted gain (ChatGPT-Luna H_i form).
Temp .85, blind gated097, v4 scorer, fresh-seed probe, misc 0. Seeds 0/1500/3000.

Usage: python flywheel_pkg20.py (3 seeds: prefix + 3 arms each)
Out: pkg20_regret.json
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
W_R, W_Q, W_N = 0.5, 0.3, 0.2  # first parametrization (sensitivity: future work)


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def tier_corr(arts):
    out = {}
    for t in (0, 1, 2):
        sub = [a for a in arts if a["tier"] == t]
        out[str(t)] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else None
    return out


def regret_pool(rounds_out):
    """Top-36 by U with live ledger regret weights over REAL rounds (the same
    shape build_ledger consumes in production — no pseudo-rounds)."""
    doc = cl.build_ledger(rounds_out, run_id="live", mode="tier")
    regrets = {f["slice"]: f["regret_of_current"] for f in doc["frontier"]}
    w = cl.regret_weights(regrets)
    kept_hist = [[a for a in x["artifacts"] if a["id"] in set(x["kept_ids"])] for x in rounds_out]
    freq = Counter(_bucket(a) for h in kept_hist for a in h)

    def u(a):
        s = f"tier={a['tier']}"
        return (W_R * w.get(s, 0.0) + W_Q * a["final_score"] / 100.0 +
                W_N * (1.0 / (1.0 + freq[_bucket(a)])))
    scored = sorted([a for h in kept_hist for a in h], key=u, reverse=True)
    seen, out = set(), []
    for a in scored:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    mean_u = round(mean(u(a) for a in out), 3) if out else None
    return out, regrets, w, mean_u


def recency_pool(kept_hist):
    src = [a for h in kept_hist[-3:] for a in h]
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


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
        pool = recency_pool(kept_hist)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[floor|plain]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        models.append(nxt)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]}", flush=True)
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
    tag = f"imp-{which}xseed{seed}"
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
        entry = {"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                 "kept_ids": sorted(kid), "probe_corr": None,
                 "regrets": {}, "artifacts": arts}
        if which == "recency":
            pool, regrets, w, mean_u = recency_pool(kept_hist), {}, {}, None
        elif which == "binary":
            pool = tC.pool_utility(kept_hist)
            regrets, w, mean_u = {}, {}, None
        else:
            pool, regrets, w, mean_u = regret_pool(rounds_out + [entry])
        m["pool_hard"] = sum(1 for a in pool if a["tier"] == 2)
        hk = [a for a in pool if a["tier"] == 2]
        m["pool_hard_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in hk), 3) if hk else None
        m["mean_pool_U"] = mean_u
        m["regret_w"] = w
        entry["regrets"] = regrets
        probe = p9.gen_batch(sm, p9.PROBE_BANK, g, 2, BASE_SEED + seed + 9000 + g * 100, f"PRB{g}-")
        for a in probe:
            a.update(h4.rule_evaluate_v4(a, "v4"))
            a["final_score"] = a["rule_score"]
        m["probe_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_tier_corr"] = tier_corr(probe)
        entry["probe_corr"] = m["probe_corr"]
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[recovery|{which}]")
        entry["pool_makeup"] = {str(r): sum(1 for a in pool if a["round"] == r)
                                for r in sorted({a["round"] for a in pool})}
        rounds_out.append(entry)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"poolhard={m['pool_hard']} U={mean_u} w={w} probehard={m['probe_tier_corr']['2']}",
              flush=True)
    rec = next((x["g"] for x in rounds_out[6:] if x["metrics"]["tier_acc"][2] >= 0.60), None)
    fin = rounds_out[-1]["metrics"]
    return {"combo": tag, "arm": which, "seed": seed, "recovery_round": rec,
            "final_hard": fin["tier_corr"]["2"], "final_acc2": fin["tier_acc"][2],
            "final_probehard": fin["probe_tier_corr"]["2"], "rounds": rounds_out}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", choices=["plain", "strat", "all"], default="all")
    args = ap.parse_args()
    plans = []
    if args.prefix in ("plain", "all"):
        plans.append(("starved", "plain"))
    if args.prefix in ("strat", "all"):
        plans.append(("banked", "strat"))
    for name, psel in plans:
        all_out = []
        for seed in SEEDS:
            state = run_prefix(seed, psel)
            for w in ["recency", "binary", "regret"]:
                all_out.append(run_arm(w, state, seed))
        with open(OUT / f"pkg20_regret_{name}.json", "w") as f:
            json.dump({"block": "regret-" + name, "combos": all_out}, f, indent=1)
        print(f"Wrote pkg20_regret_{name}.json")


if __name__ == "__main__":
    main()

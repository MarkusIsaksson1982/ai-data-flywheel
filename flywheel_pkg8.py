"""
Package 8 — Quarantined reset vs deep misconception lock-in (frozen platform)
==============================================================================
LAST UNFALSIFIED INTERVENTION (pkg7): every selector-only rescue failed deep
lock-in (corr 0.08-0.25, misc 0.30-0.52); purge needs correct-mass >= kept-size
which a degraded model cannot supply. Only generation repair is untested.

PREFIX (per seed): G0-G5 flat normal, topk + invert-pure0, misc_init 0.35.
Guard: G5 misc_rate >= 0.30 AND main <= 0.35.
FORK from M_6 (model trained at G5 end under disease) for rounds 10-13:
  A disease : invert pure0 sel + invert-ranked recency pools (pkg7-A replica;
              doubles as cross-turn determinism check)
  B repair  : blind fixed05, top-18 final, recency-by-final (pkg7-B replica)
  Q1 reset+quarantine: fresh SM0; init pool = golden(24, misc-free by
       construction) + screened prefix R0-R2 kept (rule>=85 AND not _misc),
       capped 36; continuation pools = screened recency (same screen, golden
       backfill if <12); frozen selection (top-18 final), blind judge, t .85
  Q2 reset-raw: fresh SM0; plain unscreened recency pools (tests whether reset
       alone suffices — predicts v5-C-style reinfection via poisoned archive)
Recovery bar: main >= 0.65 AND model misc < 0.05 by round 13.
Probe every round (margins + continuity). Growth 0 (misc is the flaw here).

Usage: python flywheel_pkg8.py (all 3 seeds)
Out: pkg8_reset.json
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
import flywheel_harness3 as h3
import flywheel_harness4 as h4
import flywheel_pkg2 as p2

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]


def gen_probe(sm, g, seed):
    rng = random.Random(BASE_SEED + seed + 9000 + g * 100)
    arts = [base.generate_artifact(sm, p, f"PRB{g}-{i:02d}", g, rng)
            for i, p in enumerate(p2.PROBE * p2.PROBE_NPP)]
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    return arts


def screen(pool):
    """Quarantine: rule-verified high-quality AND provably non-misc."""
    return [a for a in pool if a["rule_score"] >= 85 and not a.get("_misc")]


def top36(cands, key):
    seen, out = set(), []
    for a in sorted(cands, key=key, reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def run_prefix(seed):
    tag = f"lockxseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["misc_rate"] = 0.35
    kept_hist, rounds_out, models = [], [], [sm]
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
        m["misc_rate"] = sm.params.get("misc_rate", 0.0)
        kept_hist.append(kept)
        hists = ([kept_hist[-3]] if len(kept_hist) >= 3 else []) + \
                ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]]
        pool = top36([a for h in hists for a in h], lambda a: a["final_score"])
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[prefix|misc+invert]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        models.append(nxt)
        sm = nxt
        print(f"PREFIX s{seed} G{g}: main={m['correct_rate']} misc={m['misc_rate']}", flush=True)
    fin = rounds_out[5]["metrics"]
    assert fin["misc_rate"] >= 0.30 and fin["correct_rate"] <= 0.35, fin
    print(f"prefix s{seed} locked (misc={fin['misc_rate']}, corr={fin['correct_rate']})")
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out}


def run_arm(which, state, seed):
    st = copy.deepcopy(state)
    tag = f"reset-{which}xseed{seed}"
    kept_hist = [list(h) for h in st["kept_hist"]]
    rounds_out = st["rounds_out"]
    if which in ("Q1", "Q2"):
        sm = base.make_sm0()
        sm.version = f"{tag}-G6fresh"
        sm.params["misc_rate"] = 0.0
        gold = h3.golden_for("legacy")
        for a in gold:
            a["final_score"] = a["rule_score"]
        assert all(not a.get("_misc") for a in gold), "golden must be misc-free"
        if which == "Q1":
            early = screen([a for h in kept_hist[:3] for a in h])
            pool0 = top36(gold + early, lambda a: a["final_score"])
            print(f"arm Q1 s{seed}: reset pool {len(pool0)} ({len(gold)} golden + "
                  f"{len(pool0)-len(gold)} screened early)", flush=True)
        else:
            pool0 = top36(gold + [a for h in kept_hist[:3] for a in h],
                          lambda a: a["final_score"])
        sm = base.train_next_sm(f"{tag}-G6", [sm], pool0, ["golden", 0, 1, 2],
                                temp_override=0.85, lesson=f"[reset|{which}]")
    else:
        sm = st["models"][-1]
    golden_ref = h3.golden_for("legacy")
    for a in golden_ref:
        a["final_score"] = a["rule_score"]
    for g in range(10, 14):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = base.generate_batch(sm, g, NPP, gs)
        if which in ("B", "Q1", "Q2"):
            h4.evaluate_v4(arts, sm, "blind", 0.5, js, (1.0, 0.0), "v4")
        else:
            h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
        kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "reset-test", tag
        m = h1.compute_round_metrics(arts, kept)
        probe = gen_probe(sm, g, seed)
        probe_corr = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_corr"] = probe_corr
        m["misc_rate"] = sm.params.get("misc_rate", 0.0)
        m["kept_misc_frac"] = round(mean(1.0 if a.get("_misc") else 0.0 for a in kept), 3)
        hists = ([kept_hist[-3]] if len(kept_hist) >= 3 else []) + \
                ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]]
        if which == "Q1":
            pool = top36(screen([a for h in hists for a in h]), lambda a: a["final_score"])
            if len(pool) < 12:
                pool = top36(pool + golden_ref, lambda a: a["final_score"])
        else:
            pool = top36([a for h in hists for a in h], lambda a: a["final_score"])
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[reset-test|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": probe_corr,
                           "pool_n": len(pool), "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt
        print(f"arm {which} s{seed} G{g}: main={m['correct_rate']} probe={probe_corr} "
              f"misc={m['misc_rate']}/k{m['kept_misc_frac']} pool={len(pool)}", flush=True)
    fin = rounds_out[-1]["metrics"]
    ok = fin["correct_rate"] >= 0.65 and fin["misc_rate"] < 0.05
    return {"combo": tag, "arm": which, "seed": seed, "recovered": ok,
            "final_main": fin["correct_rate"], "final_probe": fin["probe_corr"],
            "final_misc": fin["misc_rate"], "rounds": rounds_out}


def main():
    all_out = []
    for seed in SEEDS:
        state = run_prefix(seed)
        for w in ["A", "B", "Q1", "Q2"]:
            all_out.append(run_arm(w, state, seed))
    with open(OUT / "pkg8_reset.json", "w") as f:
        json.dump({"block": "reset", "combos": all_out}, f, indent=1)
    print("Wrote pkg8_reset.json")


if __name__ == "__main__":
    main()

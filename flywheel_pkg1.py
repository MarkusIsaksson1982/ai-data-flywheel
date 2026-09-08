"""
Package 1 — Divergent-parent merging (Thread-C loose end, frozen platform)
==========================================================================
FREEZE CONFIRMED (locked, imported, not modified):
  Base DEFAULTS: scorer v4, judge blind, gated097, simple recency import,
  misc 0, drift-vs-G0 + wrongmode tracking, multi-seed claims.
  Lineage layer (Thread C): recency-36 default, single-parent default,
  multi-parent only above complementarity gate 0.5, pool_makeup / archive
  usage / mean pool quality tracked. Reference: harness5_baseline.json.

DESIGN: shared G0, then two parallel lineages for G1-G2:
  exploit: temp 0.55, strict top-12 selection per batch (36 generated)
  explore: temp 1.20, loose top-24 selection per batch
Branch RNG streams offset by +5000 on explore (else identical batches).
At G3, arms diverge (matched 36-pools, recency over relevant archive):
  single      : exploit-G2 continued (control; pool: exploit archive)
  pair_same   : merge(exploit-G1, exploit-G2) (expect null replication)
  pair_div    : merge(exploit-G2, explore-G2) (the test)
Continuation single-parent from the G3 model; current-batch selection fixed
top-18 everywhere (isolates parent/pool effects, as in Thread C).
Protocols: normal (G0-G5, merge at G3) and collapse (G0-G7: merge G3,
light ramp G4-5 topk-14/10, recovery G6-7). Seeds 0/1500/3000.
Merge machinery: threadC.merge_train (equal-weight param mean). Metric of
interest: gain = merged_endpoint - best-single_endpoint vs complementarity
(jaccard distance of branch kept pid sets at merge).

Usage: python flywheel_pkg1.py --block p1_normal|p1_collapse|all
Out: pkg1_{block}.json
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
import flywheel_harness2 as h2
import flywheel_harness3 as h3
import flywheel_harness4 as h4
import flywheel_threadC as tC

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
POOL_CAP = 36
SEEDS = [0, 1500, 3000]
PHASE8 = {0: "normal", 1: "normal", 2: "normal", 3: "normal",
          4: "collapse", 5: "collapse", 6: "recovery", 7: "recovery"}
LIGHT_KS = {4: 14, 5: 10}
LIGHT_TEMPS = {4: 0.80, 5: 0.65}


def _gen_eval(sm, g, seed, branch, scorer="v4"):
    gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
    if branch == "explore":
        gs += 5000
        js += 5000
    arts = base.generate_batch(sm, g, NPP, gs)
    if g == 0:
        for a in arts:
            a.update(h4.rule_evaluate_v4(a, scorer))
            a.update({"judge_version": None, "judge_score": None,
                      "final_score": a["rule_score"], "eval_mix": "rule-only",
                      "judge_kind": None, "alpha_rule": None})
    else:
        # frozen gated097 rule would need prev stats; branches track their own:
        h4.evaluate_v4(arts, sm, "blind", 0.5, js, (1.0, 0.0), scorer)
    for a in arts:
        a["branch"] = branch
    return arts


def _branch_pool(hist):
    """Recency-36 over a branch's own kept history (last 2 gens)."""
    src = ([hist[-2]] if len(hist) >= 2 else []) + [hist[-1]]
    flat = sorted([a for h in src for a in h], key=lambda a: a["final_score"], reverse=True)
    seen, out = set(), []
    for a in flat:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= POOL_CAP:
            break
    return out


def _combined_pool(hist_x, hist_e):
    flat = sorted([a for h in hist_x[-2:] + hist_e[-2:] for a in h],
                  key=lambda a: a["final_score"], reverse=True)
    seen, out = set(), []
    for a in flat:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= POOL_CAP:
            break
    return out


def run_arm(arm, seed, n_rounds):
    tag = f"{arm}xseed{seed}"
    sm0 = base.make_sm0()
    sm0.version = f"{tag}-G0"
    # branch states: exploit + explore lineages (models + kept hists)
    bx = {"sm": None, "hist": [], "models": []}
    be = {"sm": None, "hist": [], "models": []}
    rounds_out: list = []
    g0dist = None
    # G0 shared
    arts0 = _gen_eval(sm0, 0, seed, "shared")
    kept0 = h1.sel_topk(arts0, [], k=18)
    kid = {a["id"] for a in kept0}
    for a in arts0:
        a["kept"], a["phase"], a["combo"] = a["id"] in kid, "normal", tag
    m0 = h1.compute_round_metrics(arts0, kept0)
    m0["drift_g0"] = 0.0
    g0dist = h4.tmpl_dist(arts0)
    rounds_out.append({"g": 0, "phase": "normal", "branch": "shared", "metrics": m0,
                       "model": sm0.to_dict(), "kept_ids": sorted(kid), "artifacts": arts0,
                       "parents": [], "complementarity": None, "pool_makeup": {}})
    for br, st, tmp, kk in (("exploit", bx, 0.55, 12), ("explore", be, 1.20, 24)):
        pool = kept0
        nxt = base.train_next_sm(f"{tag}-{br}-G1", [sm0], pool, [0],
                                 temp_override=tmp, lesson=f"[{br} branch init]")
        st["sm"], st["models"] = nxt, [sm0, nxt]
    # G1-G2 branches
    for g in (1, 2):
        for br, st, tmp, kk in (("exploit", bx, 0.55, 12), ("explore", be, 1.20, 24)):
            arts = _gen_eval(st["sm"], g, seed, br)
            kept = h1.sel_topk(arts, st["hist"], k=kk)
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "normal", tag
            m = h1.compute_round_metrics(arts, kept)
            m["drift_g0"] = h4.tvd(h4.tmpl_dist(arts), g0dist)
            m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
            pool = _branch_pool(st["hist"] + [kept])
            nxt = base.train_next_sm(f"{tag}-{br}-G{g+1}", [st["sm"]], pool, [g],
                                     temp_override=tmp, lesson=f"[{br} continue]")
            rounds_out.append({"g": g, "phase": "normal", "branch": br, "metrics": m,
                               "model": st["sm"].to_dict(), "kept_ids": sorted(kid),
                               "artifacts": arts, "parents": [st["sm"].version],
                               "complementarity": None,
                               "pool_makeup": {str(r): sum(1 for a in pool if a["round"] == r)
                                               for r in sorted({a["round"] for a in pool})}})
            st["hist"].append(kept)
            st["sm"] = nxt
            st["models"].append(nxt)
    # merge / control at G3
    # complementarity = jaccard distance of cumulative branch kept pid sets
    px = {a["problem_id"] for h in bx["hist"] for a in h}
    pe = {a["problem_id"] for h in be["hist"] for a in h}
    compl = tC._jaccard(px, pe)
    if arm == "single":
        parents = [bx["models"][-1]]
        pool = _branch_pool(bx["hist"])
    elif arm == "pair_same":
        parents = bx["models"][-2:]
        pool = _branch_pool(bx["hist"])
    elif arm == "pair_div":
        parents = [bx["models"][-1], be["models"][-1]]
        pool = _combined_pool(bx["hist"], be["hist"])
    else:
        raise ValueError(arm)
    src_rounds = sorted({a["round"] for a in pool})
    if len(parents) == 1:
        sm = base.train_next_sm(f"{tag}-MERGED-G3", parents, pool, src_rounds,
                                temp_override=0.85, lesson=f"[merge:{arm}]")
    else:
        sm = tC.merge_train(f"{tag}-MERGED-G3", parents, pool, src_rounds,
                            lesson=f"[merge:{arm}]")
        sm.params["temperature"] = 0.85
    merge_info = {"parents": [p.version for p in parents], "complementarity": compl,
                  "pool_makeup": {str(r): sum(1 for a in pool if a["round"] == r) for r in src_rounds}}
    # continuation (single-parent from merged model; archive = branch hists)
    kept_hist: list = [kept0] + (bx["hist"] + be["hist"] if arm == "pair_div" else bx["hist"])
    for g in range(3, n_rounds):
        phase = "normal" if n_rounds == 6 else PHASE8[g]
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        arts = base.generate_batch(sm, g, NPP, gs)
        h4.evaluate_v4(arts, sm, "blind", 0.5, js, (1.0, 0.0), "v4")
        for a in arts:
            a["branch"], a["combo"], a["phase"] = "merged", tag, phase
        if phase == "collapse":
            kept = h1.sel_topk(arts, kept_hist, k={4: 14, 5: 10}[g])
            sel_name = f"topk-{ {4: 14, 5: 10}[g]} (light)"
        else:
            kept = h1.sel_topk(arts, kept_hist, k=18)
            sel_name = "topk-18"
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"] = a["id"] in kid
        m = h1.compute_round_metrics(arts, kept)
        m["drift_g0"] = h4.tvd(h4.tmpl_dist(arts), g0dist)
        m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
        pool = tC.pool_recency(kept_hist + [kept])
        makeup = {str(r): sum(1 for a in pool if a["round"] == r) for r in sorted({a["round"] for a in pool})}
        temp = {4: 0.80, 5: 0.65}.get(g, 0.90 if phase == "recovery" else 0.85) if n_rounds == 8 else 0.85
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=temp, lesson=f"[{phase} continue]")
        entry = {"g": g, "phase": phase, "branch": "merged", "metrics": m,
                 "model": sm.to_dict(), "kept_ids": sorted(kid), "artifacts": arts,
                 "parents": [sm.version], "complementarity": None, "pool_makeup": makeup}
        if g == 3:
            entry["merge"] = merge_info
        rounds_out.append(entry)
        kept_hist.append(kept)
        sm = nxt
        print(f"{tag} G{g} [{phase}/{arm}]: corr={m['correct_rate']} cov={m['category_coverage']} "
              f"pool={makeup}", flush=True)
    # baseline = weaker of the two branch-G2 batches (what the merge must beat)
    br2 = [x for x in rounds_out if x.get("branch") in ("exploit", "explore") and x["g"] == 2]
    base_cov = round(min(x["metrics"]["category_coverage"] for x in br2), 3)
    base_q = round(min(x["metrics"]["correct_rate"] for x in br2), 3)
    fin = rounds_out[-1]["metrics"]
    return {"combo": tag, "arm": arm, "seed": seed,
            "complementarity": compl, "baseline_cov": base_cov, "baseline_q": base_q,
            "cov_margin": round(fin["category_coverage"] - base_cov, 3),
            "q_margin": round(fin["correct_rate"] - (base_q - 0.05), 3),
            "rounds": rounds_out}


BLOCKS = {
    "p1_normal": [(a, o, 6) for a in ["single", "pair_same", "pair_div"] for o in SEEDS],
    "p1_collapse": [(a, o, 8) for a in ["single", "pair_same", "pair_div"] for o in SEEDS],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["p1_normal", "p1_collapse", "all"], default="all")
    args = ap.parse_args()
    blocks = BLOCKS if args.block == "all" else {args.block: BLOCKS[args.block]}
    for name, combos in blocks.items():
        print(f"--- block {name}: {len(combos)} combos ---")
        results = [run_arm(*c) for c in combos]
        with open(OUT / f"pkg1_{name}.json", "w") as f:
            json.dump({"block": name, "combos": results}, f, indent=1)
        print(f"Wrote pkg1_{name}.json")


if __name__ == "__main__":
    main()

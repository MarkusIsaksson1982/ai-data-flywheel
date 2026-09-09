"""
Package 24 — Disagreement case: scalar fires, per-slice vetoes (frozen platform)
=================================================================================
pkg21 residue: scalar pid-DIVERGENCE and per-slice C_pair gain AGREED in every
observed fork, so the veto was never load-bearing. (Note v1 post-mortem:
tC._jaccard returns 1-|A&B|/|A|B| — DIVERGENCE, not overlap. A same-curriculum
pid-matched v1 run scored scalar 0.14-0.27 and vetoed everywhere, preserved as
pkg24_disagree_v1_fallback.json — where it accidentally showed fallback arms
underperforming pure single via polluted pool history.) This v2 FORCES the
disagreement the gates are built for:
  disjoint curricula: E (strong) on easy+med {0,1} blind-selected correct, W
  (weak/poisoned teacher of unseen material) on hard {2} invert-selected
  confident-wrong => scalar divergence ~1.0, FIRES merge.
  no quality complementarity: W kept tier-correct ~0, lineage cbest ~= cE =>
  pair gain ~0, VETOES merge.
Arms G4-G7 (pkg21 arm loop verbatim): single (best=E), scalar (must merge),
slicemerge (must fall back). Prediction: scalar arm HURT vs single (stale
invert-inflated final_scores drag W's wrong arts into the union merge pool);
slicemerge == single. A hurt verdict kills scalar-only gating; a hold verdict
bounds the pollution mechanism instead.
Single round-fork (G1-G3) + arms to G7: no multi-round forgetting dynamics, so
the gate decision is the only treatment (pkg23 confound controlled by design).

Usage: python flywheel_pkg24.py (3 seeds)
Out: pkg24_disagree.json
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness4 as h4
import flywheel_pkg9 as p9
import flywheel_threadC as tC
import capability_ledger as cl

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
SCALAR_GATE = 0.5
GAIN_GATE = 0.05
E_DIET = {0, 1}
W_DIET = {2}  # disjoint curriculum => pid-DIVERGENCE ~1.0 => scalar FIRES


def tier_corr(arts):
    out = {}
    for t in (0, 1, 2):
        sub = [a for a in arts if a["tier"] == t]
        out[str(t)] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else None
    return out


def branch_pool(kept_hist, allowed):
    src = [a for h in kept_hist[-3:] for a in h if a["tier"] in allowed]
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def kept_tier_correct_rate(kept_hist, tier):
    sub = [a for h in kept_hist[-2:] for a in h if a["tier"] == tier]
    return round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else 0.0


def cell_rates(kept):
    out = {}
    for t in (0, 1, 2):
        sub = [a for a in kept if a["tier"] == t]
        out[str(t)] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else 0.0
    return out


def run_seed(seed):
    tag = f"disagreexseed{seed}"
    sm0 = base.make_sm0()
    sm0.version = f"{tag}-G0"
    assert sm0.params["tier_acc"] == [0.55, 0.55, 0.55]
    branches = {}
    rounds_log = []
    prev_corr, prev_bias = None, None
    # G0 shared (pkg21 verbatim, rule-only)
    gs, js = BASE_SEED + seed, BASE_SEED + seed + 11
    sm0.params["temperature"] = 0.85
    arts = p9.gen_batch(sm0, p9.BANK, 0, NPP, gs, "R0-")
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a.update({"judge_version": None, "judge_score": None,
                  "final_score": a["rule_score"], "eval_mix": "rule-only",
                  "judge_kind": None, "alpha_rule": None})
    kept0 = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
    kid = {a["id"] for a in kept0}
    for a in arts:
        a["kept"], a["phase"], a["combo"] = a["id"] in kid, "branch", tag
    m0 = h1.compute_round_metrics(arts, kept0)
    m0["tier_corr"] = tier_corr(arts)
    rounds_log.append({"g": 0, "branch": "shared", "metrics": m0, "model": sm0.to_dict(),
                       "kept_ids": sorted(kid), "artifacts": arts})
    for br in ("E", "W"):
        diet = E_DIET if br == "E" else W_DIET
        pool = [a for a in kept0 if a["tier"] in diet][:36] or list(kept0)[:36]
        nxt = base.train_next_sm(f"{tag}-{br}-G1", [sm0], pool, [0],
                                 temp_override=0.85, lesson=f"[branch|{br}]")
        branches[br] = {"sm": nxt, "hist": [kept0], "models": [sm0, nxt]}
    # G1-G3 disjoint-curriculum divergence: E keeps blind-selected correct on
    # easy+med, W keeps invert-selected confident-wrong on hard (a bad teacher
    # of unseen material). Scalar divergence ~1.0 FIRES; W tier-correct ~0
    # keeps pair gain ~0, VETOES. e_pids capture removed (v1 pid-match).
    for g in range(1, 4):
        for br in ("E", "W"):
            st = branches[br]
            sm = st["sm"]
            gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
            sm.params["temperature"] = 0.85
            arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{br}-")
            if br == "E":
                alpha = 0.8 if (prev_corr is not None and
                                (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
                h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
                kept = []
                for t in sorted(E_DIET):
                    kept.extend(sorted([a for a in arts if a["tier"] == t],
                                       key=lambda a: a["final_score"], reverse=True)[:9])
            else:
                h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
                kept = sorted([a for a in arts if a["tier"] == 2],
                              key=lambda a: a["final_score"], reverse=True)[:18]
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "branch", tag
            m = h1.compute_round_metrics(arts, kept)
            m["tier_corr"] = tier_corr(arts)
            m["tier_acc"] = list(sm.params["tier_acc"])
            m["kept_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in kept), 3)
            st["hist"].append(kept)
            pool = branch_pool(st["hist"], E_DIET if br == "E" else W_DIET)
            nxt = base.train_next_sm(f"{tag}-{br}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[branch|{br}]")
            rounds_log.append({"g": g, "branch": br, "metrics": m, "model": sm.to_dict(),
                               "kept_ids": sorted(kid), "artifacts": arts})
            st["sm"] = nxt
            st["models"].append(nxt)
            if br == "E":
                prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
            print(f"{tag} {br} G{g}: keptcorr={m['kept_corr']} acc={m['tier_acc']}", flush=True)
    # fork stats (pkg21 verbatim, E/W instead of E/H)
    lineage_cells = [cell_rates(kept0)]
    for br in ("E", "W"):
        for h in branches[br]["hist"]:
            lineage_cells.append(cell_rates(h))
    cbest = {s: max(c[s] for c in lineage_cells) for s in ("0", "1", "2")}
    denom = sum(cbest.values()) or 1.0
    px = {a["problem_id"] for h in branches["E"]["hist"][-2:] for a in h}
    pe = {a["problem_id"] for h in branches["W"]["hist"][-2:] for a in h}
    scalar_compl = tC._jaccard(px, pe)
    cE = {str(t): kept_tier_correct_rate(branches["E"]["hist"], t) for t in (0, 1, 2)}
    cW = {str(t): kept_tier_correct_rate(branches["W"]["hist"], t) for t in (0, 1, 2)}
    cp = cl.pair_coverage(cE, cW, cbest)
    sing_cov = max(sum(cE.values()) / denom, sum(cW.values()) / denom)
    gain = round(cp - sing_cov, 3)
    print(f"{tag} FORK compl: scalar={scalar_compl} C_pair={cp} gain={gain} cE={cE} cW={cW}",
          flush=True)
    out = []
    for arm in ["single", "scalar", "slicemerge"]:
        st = copy.deepcopy({"E": branches["E"], "W": branches["W"]})
        models = {"E": st["E"]["sm"], "W": st["W"]["sm"]}
        qE = mean(1.0 if a["correct"] else 0.0
                  for h in st["E"]["hist"][-2:] for a in h)
        qW = mean(1.0 if a["correct"] else 0.0
                  for h in st["W"]["hist"][-2:] for a in h)
        best_br = "E" if qE >= qW else "W"
        if arm == "single":
            parents, how = [models[best_br]], "best-single"
        elif arm == "scalar":
            parents, how = ([models["E"], models["W"]], "merged") \
                if scalar_compl > SCALAR_GATE else ([models[best_br]], "single-fallback")
        else:
            parents, how = ([models["E"], models["W"]], "merged") \
                if gain > GAIN_GATE else ([models[best_br]], "single-fallback")
        atag = f"{arm}xseed{seed}"
        if len(parents) == 1:
            pool1 = branch_pool(st[best_br]["hist"], {0, 1, 2})
            sm = base.train_next_sm(f"{atag}-G4", parents, pool1, [3],
                                    temp_override=0.85, lesson=f"[merge|{arm}:{how}]")
        else:
            pool = []
            for h in st["E"]["hist"][-2:] + st["W"]["hist"][-2:]:
                pool.extend(h)
            seen, poolu = set(), []
            for a in sorted(pool, key=lambda a: a["final_score"], reverse=True):
                if a["id"] not in seen:
                    seen.add(a["id"])
                    poolu.append(a)
                if len(poolu) >= 36:
                    break
            sm = tC.merge_train(f"{atag}-G4", parents, poolu, [2, 3], lesson=f"[merge|{arm}:{how}]")
            sm.params["temperature"] = 0.85
            wfrac = mean(1.0 if "-W-" in a["id"] else 0.0 for a in poolu)
            warts = [a for a in poolu if "-W-" in a["id"]]
            wcorr = round(mean(1.0 if a["correct"] else 0.0 for a in warts), 2) if warts else None
            print(f"{atag} mergepool: Wshare={wfrac:.2f} Wcorr={wcorr}", flush=True)
        kept_hist = [h for h in st[best_br]["hist"]] if arm == "single" \
            else [h for h in st["E"]["hist"]] + [h for h in st["W"]["hist"]]
        rounds, pc, pb = [], None, None
        for g in range(4, 8):
            gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
            sm.params["temperature"] = 0.85
            arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{arm}-")
            alpha = 0.8 if (pc is not None and (pc < 0.97 or abs(pb or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
            kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "merge", atag
            m = h1.compute_round_metrics(arts, kept)
            m["tier_corr"] = tier_corr(arts)
            m["tier_acc"] = list(sm.params["tier_acc"])
            kept_hist.append(kept)
            pool = branch_pool(kept_hist, {0, 1, 2})
            nxt = base.train_next_sm(f"{atag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[merge|{arm}]")
            rounds.append({"g": g, "arm": arm, "how": how if g == 4 else "continue",
                           "metrics": m, "model": sm.to_dict(), "kept_ids": sorted(kid),
                           "artifacts": arts})
            sm = nxt
            pc, pb = m["judge_corr"], m["leniency_bias"]
            print(f"{atag} G{g}: tiers={m['tier_corr']} acc={m['tier_acc']}", flush=True)
        out.append({"combo": atag, "arm": arm, "seed": seed, "how": how,
                    "scalar_compl": scalar_compl, "pair_gain": gain, "rounds": rounds})
    return {"branch_log": rounds_log,
            "fork": {"scalar_compl": scalar_compl, "pair_coverage": cp, "gain": gain,
                     "cE": cE, "cW": cW},
            "combos": out}


def main():
    all_out, forks = [], []
    for seed in SEEDS:
        r = run_seed(seed)
        forks.append({"seed": seed, **r["fork"]})
        all_out.extend(r["combos"])
    with open(OUT / "pkg24_disagree.json", "w") as f:
        json.dump({"block": "disagree", "forks": forks, "combos": all_out}, f, indent=1)
    print("Wrote pkg24_disagree.json")


if __name__ == "__main__":
    main()

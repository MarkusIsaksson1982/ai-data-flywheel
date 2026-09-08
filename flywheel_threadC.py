"""
Thread C — Lineage, Archive Value & Multi-Parent Reuse (on the frozen platform)
===============================================================================
FREEZE (locked; v1-v5 code untouched, imported as library):
  DEFAULTS = scorer v4 + judge blind + gated097 mixing + simple recency import
  + misc_init 0 + drift-vs-G0 + wrongmode tracking + multi-seed awareness.
  Reference: harness5_baseline.json. Frozen library: flywheel_sim + harness1-4.

THREAD-C QUESTIONS:
  Q1. Which historical rounds/artifacts/models should be re-imported/merged?
  Q2. When does multi-parent merging beat single-parent continuation?
  Q3. Can a lightweight archive-utility score predict downstream benefit?

MACHINERY (new here; generation/scorer/judge/metrics reused from frozen lib):
  Archive: every round logs kept set + model + metadata (round, coverage,
    quality, misc_rate, drift, parentage, kept pid set). Pools capped at 36
    in all arms (matched data budgets).
  Reuse policies (pool builders over the full archive):
    recency    : top-36 by final from {R_{t-2}, R_{t-1}, last} (current default)
    topk_hist  : top-36 by final from ALL history (recency-blind quality)
    utility    : top-36 by U = 0.50*final/100 + 0.25*novelty + 0.25*need, where
                 novelty = 1/(1+bucket count over archive),
                 bucket = (pid, correct, len-bin),
                 need = 1 if pid forgotten-or-weak (last-kept pid correct
                 rate < 0.5 or pid absent) else 0.
  Multi-parent merge (merge_train): numeric params = equal-weight mean over
    parents (documented choice; quality-weighting left as variant), lessons
    concatenated, lineage lists ALL parents + source rounds. Single-parent
    arms use base.train_next_sm (primary parent only).
  Parent heuristics: single_best (best kept-correct among last 3 gens),
    pair_best (top-2 of last 3 merged), pair_compl (among last 4, max
    jaccard-distance of kept pid sets + 0.5*mean quality).

PROTOCOLS (all frozen defaults unless noted; seeds 0/1500/3000):
  c_normal   : 6 rounds normal. policies recency/topk_hist/utility (single parent).
  c_collapse : 8 rounds: G0-2 normal, G3-4 LIGHT ramp (topk-14/10, temps .8/.65),
               G5-7 recovery. Same 3 policies (single parent).
  c_parents  : 8 rounds, light ramp, pool fixed utility-36.
               modes single_best / pair_best / pair_compl.
  c_misc     : 6 rounds normal, misc_init 0.15 (mild contamination, blind judge
               purges it per v4 — tests robustness drag). policies recency/utility.
               misc-0 controls already exist in c_normal.

NEW METRICS (on top of frozen suite): pool_makeup {src_round: n}, parent_ids,
  parent_complementarity (jaccard distance, None if single), mean_pool_U,
  recovery_speed (first G>=5 at/above baseline cov and q-0.05), scar margins,
  archive usage histogram (how often each round's kept entered pools).

Usage: python flywheel_threadC.py --block c_normal|c_collapse|c_parents|c_misc|all
Out: threadC_{block}.json
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

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
POOL_CAP = 36
SEEDS = [0, 1500, 3000]
LIGHT_KS = {3: 14, 4: 10}
LIGHT_TEMPS = {3: 0.80, 4: 0.65}
PHASE8 = {0: "normal", 1: "normal", 2: "normal", 3: "collapse",
          4: "collapse", 5: "recovery", 6: "recovery", 7: "recovery"}

FROZEN_DEFAULTS = {"scorer": "v4", "judge": "blind", "alpha_mode": "gated097",
                   "import_mode": "simple", "misc_init": 0.0, "seed_offset": 0}


# ----------------------------------------------------------------------------
# A. reuse-policy pool builders (all cap POOL_CAP = matched budgets)
# ----------------------------------------------------------------------------
def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def _dedup_top(cands, cap):
    seen, out = set(), []
    for a in cands:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= cap:
            break
    return out


def pool_recency(kept_hist):
    """Default: top-36 by final from {R_{t-2}, R_{t-1}, last}."""
    h = kept_hist
    src = (h[-3] if len(h) >= 3 else []) + (h[-2] if len(h) >= 2 else []) + h[-1]
    return _dedup_top(sorted(src, key=lambda a: a["final_score"], reverse=True), POOL_CAP)


def pool_topk_hist(kept_hist):
    """Recency-blind quality: top-36 by final from ALL history."""
    src = sorted([a for h in kept_hist for a in h],
                 key=lambda a: a["final_score"], reverse=True)
    return _dedup_top(src, POOL_CAP)


def pool_utility(kept_hist):
    """U = 0.50*quality + 0.25*novelty + 0.25*need(target weak/forgotten pids)."""
    last = kept_hist[-1]
    by_pid: dict[str, list] = {}
    for a in last:
        by_pid.setdefault(a["problem_id"], []).append(a)
    weak = {p["pid"] for p in base.PROBLEMS
            if not by_pid.get(p["pid"]) or
            mean(1.0 if a["correct"] else 0.0 for a in by_pid[p["pid"]]) < 0.5}
    freq = Counter(_bucket(a) for h in kept_hist for a in h)
    def u(a):
        return (0.50 * a["final_score"] / 100.0
                + 0.25 * (1.0 / (1.0 + freq[_bucket(a)]))
                + 0.25 * (a["problem_id"] in weak))
    src = sorted([a for h in kept_hist for a in h], key=u, reverse=True)
    return _dedup_top(src, POOL_CAP)


POOLS = {"recency": pool_recency, "topk_hist": pool_topk_hist, "utility": pool_utility}


# ----------------------------------------------------------------------------
# B. multi-parent merge + parent heuristics
# ----------------------------------------------------------------------------
def merge_train(new_version, parents: list, kept, data_rounds, lesson=""):
    """Equal-weight mean of numeric params; concatenated lessons; full lineage."""
    lr = 0.45
    new_params: dict = {}
    for k in parents[0].params:
        vals = [p.params.get(k, 0) for p in parents]
        new_params[k] = round(sum(vals) / len(vals), 3) if isinstance(vals[0], (int, float)) else vals[0]
    # distillation drift toward kept set (same heuristic as base, from merged start)
    if kept:
        corr = mean(1.0 if a["correct"] else 0.0 for a in kept)
        fmt = mean(1.0 if a["format_ok"] else 0.0 for a in kept)
        new_params["arithmetic_acc"] = round((1 - lr) * new_params["arithmetic_acc"] + lr * (0.35 + 0.65 * corr), 3)
        new_params["format_rel"] = round((1 - lr) * new_params["format_rel"] + lr * (0.30 + 0.70 * fmt), 3)
        new_params["misc_rate"] = round((1 - lr) * new_params.get("misc_rate", 0.0)
                                        + lr * mean(1.0 if a.get("_misc") else 0.0 for a in kept), 3)
    tmpl = parents[-1].prompt_template + " " + lesson
    cap = (f"Merged {len(parents)} parents on {len(kept)} arts from rounds {data_rounds}.")
    return base.SimulatedModel(version=new_version, capability=cap, params=new_params,
                               prompt_template=tmpl,
                               lineage={"parent_models": [p.version for p in parents],
                                        "data_rounds": list(data_rounds), "n_source": len(kept)},
                               notes=lesson)


def _pidset(model_version, arch):
    for r in arch:
        if r["model"].version == model_version:
            return set(a["problem_id"] for a in r["kept"])
    return set()


def _qual(model_version, arch):
    for r in arch:
        if r["model"].version == model_version:
            k = r["kept"]
            return mean(1.0 if a["correct"] else 0.0 for a in k) if k else 0.0
    return 0.0


def pick_parents(mode, recent_models: list, arch):
    """recent_models: oldest->newest SimModels. Returns (parents, compl_or_None)."""
    cands = recent_models[-3:]
    if mode == "single_best" or len(cands) == 1:
        best = max(cands, key=lambda p: _qual(p.version, arch))
        return [best], None
    if mode == "pair_best":
        top2 = sorted(cands, key=lambda p: _qual(p.version, arch), reverse=True)[:2]
        return top2, _jaccard(_pidset(top2[0].version, arch), _pidset(top2[1].version, arch))
    if mode == "pair_compl":
        cands4 = recent_models[-4:]
        best, best_score = None, -1.0
        for i in range(len(cands4)):
            for j in range(i + 1, len(cands4)):
                a, b = cands4[i], cands4[j]
                jd = _jaccard(_pidset(a.version, arch), _pidset(b.version, arch))
                score = jd + 0.5 * (_qual(a.version, arch) + _qual(b.version, arch)) / 2
                if score > best_score:
                    best, best_score = (a, b), score
        return list(best), _jaccard(_pidset(best[0].version, arch), _pidset(best[1].version, arch))
    raise ValueError(mode)


def _jaccard(a: set, b: set):
    if not a and not b:
        return 0.0
    return round(1 - len(a & b) / max(1, len(a | b)), 3)


# ----------------------------------------------------------------------------
# C. driver
# ----------------------------------------------------------------------------
def run_combo(reuse, parent_mode, seed_offset, misc_init, n_rounds, light_collapse):
    tag = f"{reuse}x{parent_mode}xseed{seed_offset}xmisc{misc_init}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["misc_rate"] = misc_init
    kept_hist: list = []
    arch: list = []          # archive entries {g, model, kept, meta}
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    g0dist = None
    for g in range(n_rounds):
        phase = "normal" if n_rounds == 6 else PHASE8[g]
        gs, js = BASE_SEED + seed_offset + g * 100, BASE_SEED + seed_offset + g * 7 + 11
        arts = base.generate_batch(sm, g, NPP, gs)
        if g == 0:
            for a in arts:
                a.update(h4.rule_evaluate_v4(a, "v4"))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only R0 scorer=v4",
                          "judge_kind": None, "alpha_rule": None})
        else:
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        if phase == "collapse" and light_collapse:
            kept = h1.sel_topk(arts, kept_hist, k=LIGHT_KS[g])
            sel_name = f"topk-{LIGHT_KS[g]} (light)"
        else:
            # Current-batch selection is FIXED to top-18 in all arms so that
            # measured differences isolate the reuse (training-pool) effect.
            kept = _select(arts, kept_hist, phase, reuse)
            sel_name = f"topk-18 [{reuse}-reuse]"
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"] = a["id"] in kid
            a["phase"], a["combo"] = phase, tag
        m = h1.compute_round_metrics(arts, kept)
        dist = h4.tmpl_dist(arts)
        if g0dist is None:
            g0dist = dist
        m["drift_g0"] = h4.tvd(dist, g0dist)
        m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
        m["misc_rate"] = sm.params.get("misc_rate", 0.0)
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        entry = {"g": g, "model": sm, "kept": kept,
                 "meta": {"coverage": m["category_coverage"], "quality": m["correct_rate"],
                          "misc": m["misc_rate"], "drift": m["drift_g0"],
                          "pids": sorted({a["problem_id"] for a in kept})}}
        arch.append(entry)
        nxt = None
        if g < n_rounds - 1:
            nphase = "normal" if n_rounds == 6 else PHASE8[g + 1]
            recent = [e["model"] for e in arch[-4:]]
            parents, compl = pick_parents(parent_mode, recent, arch)
            pool = POOLS[reuse](kept_hist + [kept])
            src_rounds = sorted({a["round"] for a in pool})
            if nphase == "collapse" and light_collapse:
                temp = LIGHT_TEMPS[g + 1]
            else:
                temp = 0.90 if nphase == "recovery" else 0.85
            lesson = f"[{phase}->{nphase}|{reuse}|{parent_mode}]"
            if len(parents) == 1:
                nxt = base.train_next_sm(f"{tag}-G{g+1}", parents, pool, src_rounds,
                                         temp_override=temp, lesson=lesson)
            else:
                nxt = merge_train(f"{tag}-G{g+1}", parents, pool, src_rounds, lesson=lesson)
                nxt.params["temperature"] = temp
            makeup = {str(r): sum(1 for a in pool if a["round"] == r) for r in src_rounds}
        else:
            parents, compl, pool, makeup, temp = [sm], None, [], {}, None
        rounds_out.append({"g": g, "phase": phase, "selection": sel_name,
                           "reuse": reuse, "parent_mode": parent_mode,
                           "parents": [p.version for p in parents], "complementarity": compl,
                           "pool_makeup": makeup,
                           "mean_pool_quality": (round(mean(a["final_score"] for a in pool), 2)
                                                 if pool else None),
                           "alpha": arts[0].get("alpha_rule"),
                           "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        print(f"{tag} G{g} [{phase}/{reuse}/{parent_mode} parents={len(parents)}]: "
              f"corr={m['correct_rate']} cov={m['category_coverage']} "
              f"pool={makeup} compl={compl} misc={m['misc_rate']}", flush=True)
    base_cov = min(rounds_out[1]["metrics"]["category_coverage"],
                   rounds_out[2]["metrics"]["category_coverage"]) if n_rounds > 3 else None
    base_q = min(rounds_out[1]["metrics"]["correct_rate"],
                 rounds_out[2]["metrics"]["correct_rate"]) if n_rounds > 3 else None
    if n_rounds == 6:
        rec_time, cov_m, q_m = None, None, None
    else:
        rec_time = next((x["g"] - 4 for x in rounds_out[5:]
                         if x["metrics"]["category_coverage"] - base_cov >= 0
                         and x["metrics"]["correct_rate"] - (base_q - 0.05) >= 0), None)
        fin = rounds_out[-1]["metrics"]
        cov_m, q_m = round(fin["category_coverage"] - base_cov, 3), round(fin["correct_rate"] - (base_q - 0.05), 3)
    usage: dict = {}
    for x in rounds_out:
        for r_, n_ in x["pool_makeup"].items():
            usage[r_] = usage.get(r_, 0) + n_
    return {"combo": tag, "reuse": reuse, "parent_mode": parent_mode,
            "seed_offset": seed_offset, "misc_init": misc_init,
            "baseline_cov": base_cov, "baseline_q": base_q,
            "recovery_time": rec_time, "cov_margin": cov_m, "q_margin": q_m,
            "archive_usage": usage, "rounds": rounds_out}


def _select(arts, kept_hist, phase, reuse):
    # selection policy for the CURRENT batch stays top-k-ish per protocol;
    # reuse policies govern TRAINING pools (the Thread-C question), except the
    # grid arm keeps its own selector for comparability where noted. Here all
    # arms select current batches with top-18 to isolate the reuse effect.
    return h1.sel_topk(arts, kept_hist, k=18)


BLOCKS = {
    "c_normal": [(r, "single_best", o, 0.0, 6, False)
                 for r in ["recency", "topk_hist", "utility"] for o in SEEDS],
    "c_collapse": [(r, "single_best", o, 0.0, 8, True)
                   for r in ["recency", "topk_hist", "utility"] for o in SEEDS],
    "c_parents": [( "utility", pm, o, 0.0, 8, True)
                  for pm in ["single_best", "pair_best", "pair_compl"] for o in SEEDS],
    "c_misc": [(r, "single_best", o, 0.15, 6, False)
               for r in ["recency", "utility"] for o in SEEDS],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["c_normal", "c_collapse", "c_parents", "c_misc", "all"], default="all")
    args = ap.parse_args()
    blocks = BLOCKS if args.block == "all" else {args.block: BLOCKS[args.block]}
    for name, combos in blocks.items():
        print(f"--- block {name}: {len(combos)} combos ---")
        results = [run_combo(*c) for c in combos]
        with open(OUT / f"threadC_{name}.json", "w") as f:
            json.dump({"block": name, "combos": results}, f, indent=1)
        print(f"Wrote threadC_{name}.json")


if __name__ == "__main__":
    main()

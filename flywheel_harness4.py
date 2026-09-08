"""
Flywheel harness v4 — decisive adversary, misconception lock-in, drift metric, coverage scorer
===============================================================================================
A. GAP-INVERTING JUDGE (`adv_invert`): j = clip(100 - 0.9*rule + N(0,5)).
   Wrong (~15) -> ~86; correct (~95) -> ~15. Inverts the ranking — the test v3
   showed was missing. Run at pure0 (expect quality collapse), fixed05
   (final ~= 50 + 0.05*rule: margin nearly erased -> near-random selection),
   gated097 (huge |bias| should trip the gate -> alpha 0.8 contains it).
B. MISCONCEPTION LOCK-IN: base sim now has guarded `misc_rate` (default 0,
   legacy streams bit-identical): deterministic fluent-wrong artifacts
   (truth+1, fixed phrasing) + `misc_rate` inheritance in training
   (selecting _misc arts raises the next gen's rate: the feedback loop).
   Combos cross misc_init {0, 0.35} with {invert, blind, fluent} x {pure0, fixed05}.
C. DRIFT-VS-BASELINE LOCK (v4 metric): drift = TVD(round template-dist, OWN G0
   dist); locked if drift > 0.35; persistence counts consecutive locked rounds
   with the same argmax template. v3's uniform-null TVD fields are kept alongside
   for direct comparison.
D. COVERAGE SCORER (`v4`): fixed scorer + completeness term
   coverage = min(1, len(cot)/len(canonical_steps[pid])) (truncation penalty
   without prose bias; capped so verbosity can't game it; conciseness term
   still punishes bloat). Weights 60/15/10/5/10. Compare fixed vs v4.

Usage: python flywheel_harness4.py --block gap|misc|cov|all
Out: harness4_{block}.json
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

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
DRIFT_THRESH = 0.35


# ----------------------------------------------------------------------------
# D. v4 scorer (fixed + coverage term)
# ----------------------------------------------------------------------------
def rule_evaluate_v4(art: dict, scorer: str = "legacy") -> dict:
    if scorer in ("legacy", "fixed"):
        return h3.rule_evaluate_v3(art, scorer)
    assert scorer == "v4"
    f = h3.rule_evaluate_v3(art, "fixed")
    n_canon = len(base.PROBLEM_BY_ID[art["problem_id"]]["steps"])
    coverage = round(min(1.0, len(art["cot"]) / max(1, n_canon)), 3)
    n = len(art["cot"])
    conc = 1.0 if 1 <= n <= 4 else (0.6 if n <= 6 else 0.3)
    score = round(100 * (0.60 * f["correct"] + 0.15 * f["step_consistency"]
                         + 0.10 * f["format_ok"] + 0.05 * conc + 0.10 * coverage), 1)
    f["coverage"] = coverage
    f["rule_score"] = score
    f["rationale"] += f" coverage {coverage:.2f}."
    f["scorer"] = "v4"
    return f


# ----------------------------------------------------------------------------
# A. evaluation with invert judge
# ----------------------------------------------------------------------------
def evaluate_v4(arts, judge_sm, kind, alpha, seed, calib, scorer):
    rng = random.Random(seed)
    for a in arts:
        r = rule_evaluate_v4(a, scorer)
        a.update(r)
        raw = h1._blind_raw(r["rule_score"], judge_sm, rng)
        if kind == "adv_invert":
            j = round(max(0, min(100, 100 - 0.9 * r["rule_score"] + rng.gauss(0, 5))), 1)
        elif kind == "blind":
            j = round(raw, 1)
        elif kind == "verifier_assisted":
            j = round(0.6 * r["rule_score"] + 0.4 * raw, 1)
        elif kind == "calibrated":
            ac, bc = calib
            j = round(max(0, min(100, ac * raw + bc)), 1)
        elif kind in ("adv_verbose", "adv_fluent", "adv_surface"):
            j = round(max(0, min(100, raw + h3.adv_bonus(kind, a) + rng.gauss(0, 5))), 1)
        else:
            raise ValueError(kind)
        a["judge_version"], a["judge_score"] = judge_sm.version, j
        a["judge_kind"], a["alpha_rule"] = kind, alpha
        a["final_score"] = round(alpha * r["rule_score"] + (1 - alpha) * j, 1)
        a["eval_mix"] = f"{kind} alpha={alpha} scorer={scorer}"
        a["rationale"] += f" Judge({kind},{judge_sm.version})={j}."


# ----------------------------------------------------------------------------
# C. drift-vs-baseline helpers
# ----------------------------------------------------------------------------
def tmpl_dist(arts):
    tids = [h2.template_id(s) for a in arts for s in a["cot"]]
    n = len(tids)
    c = Counter(tids)
    return [c.get(t, 0) / n for t in range(h3.N_TMPL)]  # N_TMPL lives in h3? no -> use 6


def tvd(p, q):
    return round(0.5 * sum(abs(a - b) for a, b in zip(p, q)), 3)


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def run_combo(policy, judge_kind, alpha_mode, import_mode, scorer, seed_offset, misc_init):
    tag = (f"{policy}x{judge_kind}x{alpha_mode}x{import_mode}x"
           f"{scorer}xseed{seed_offset}xmisc{misc_init}")
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["misc_rate"] = misc_init
    kept_hist: list = []
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    calib = (1.0, 0.0)
    g0dist = None
    prev_arg, prev_locked, dstreak = None, False, 0
    for g in range(8):
        phase = h2.PHASE_OF[g]
        gs, js = BASE_SEED + seed_offset + g * 100, BASE_SEED + seed_offset + g * 7 + 11
        arts = base.generate_batch(sm, g, NPP, gs)
        if g == 0:
            for a in arts:
                a.update(rule_evaluate_v4(a, scorer))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": f"rule-only R0 scorer={scorer}",
                          "judge_kind": None, "alpha_rule": None})
        else:
            if judge_kind == "calibrated":
                gl = h3.golden_for(scorer if scorer in ("legacy", "fixed") else "fixed")
                jr = random.Random(777)
                calib = h1._fit_affine([h1._blind_raw(x["rule_score"], sm, jr) for x in gl],
                                       [x["rule_score"] for x in gl])
            if alpha_mode == "pure0":
                alpha = 0.0
            elif alpha_mode == "gated097":
                alpha = 0.8 if (prev_corr is not None and
                                (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            else:
                alpha = 0.5
            evaluate_v4(arts, sm, judge_kind, alpha, js, calib, scorer)
        if phase == "collapse":
            kept = h1.sel_topk(arts, kept_hist, k=h2.RAMP_KS[g])
            sel_name = f"topk-{h2.RAMP_KS[g]} (ramp)"
        else:
            kept = h1.POLICIES[policy](arts, kept_hist)
            sel_name = policy + ("+util-import" if phase == "recovery" and import_mode == "utility" else "")
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"] = a["id"] in kid
            a["phase"], a["combo"] = phase, tag
        m = h1.compute_round_metrics(arts, kept)
        tvd_u, dom_u = h3.template_tvd(arts)
        m["template_tvd"], m["tvd_dom_template"] = tvd_u, dom_u
        dist = tmpl_dist(arts)
        if g0dist is None:
            g0dist = dist
        drift = tvd(dist, g0dist)
        arg = max(range(6), key=lambda t: dist[t])
        locked = drift > DRIFT_THRESH
        if locked and prev_locked and arg == prev_arg:
            dstreak += 1
        elif locked:
            dstreak = 1
        else:
            dstreak = 0
        prev_arg, prev_locked = arg, locked
        m["drift_g0"], m["drift_argmax"], m["drift_locked"] = drift, arg, locked
        m["drift_persist"] = dstreak
        m["wrong_answer_mode"] = h3.wrong_answer_mode(kept)
        m["kept_misc_frac"] = round(mean(1.0 if a.get("_misc") else 0.0 for a in kept), 3) if kept else 0.0
        m["misc_rate"] = sm.params.get("misc_rate", 0.0)
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        nxt = None
        if g < 7:
            nphase = h2.PHASE_OF[g + 1]
            if nphase == "collapse":
                pool, temp = kept, h2.RAMP_TEMPS[g + 1]
            elif nphase == "recovery":
                pool = h2.simple_pool(kept_hist + [kept], g + 1) if import_mode == "simple" \
                    else h2.utility_pool(kept_hist + [kept], g + 1)
                temp = 0.90
            else:
                pool, temp = kept, 0.85
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [g], temp_override=temp,
                                     lesson=f"[{phase}->{nphase}|{sel_name}|{judge_kind}/{alpha_mode}|{scorer}]")
            if nphase == "collapse":
                nxt.params["diversity"] = max(0.2, sm.params["diversity"] - 0.10)
        rounds_out.append({"g": g, "phase": phase, "selection": sel_name,
                           "alpha": arts[0].get("alpha_rule"), "calib": calib,
                           "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        print(f"{tag} G{g} [{phase}/{sel_name} a={arts[0].get('alpha_rule')}]: "
              f"corr={m['correct_rate']} cov={m['category_coverage']} "
              f"drift={drift}(#{arg}){'L' if locked else ''}+{dstreak} "
              f"wrongmode={m['wrong_answer_mode']} misc={m['misc_rate']}/kept{m['kept_misc_frac']} "
              f"jcorr={m['judge_corr']} bias={m['leniency_bias']}", flush=True)
    base_cov = min(rounds_out[1]["metrics"]["category_coverage"],
                   rounds_out[2]["metrics"]["category_coverage"])
    base_q = min(rounds_out[1]["metrics"]["correct_rate"],
                 rounds_out[2]["metrics"]["correct_rate"])
    fin = rounds_out[7]["metrics"]
    rec_time = next((i - 5 for i in (6, 7)
                     if rounds_out[i]["metrics"]["category_coverage"] - base_cov >= 0
                     and rounds_out[i]["metrics"]["correct_rate"] - (base_q - 0.05) >= 0), None)
    return {"combo": tag, "policy": policy, "judge": judge_kind, "alpha_mode": alpha_mode,
            "import_mode": import_mode, "scorer": scorer, "seed_offset": seed_offset,
            "misc_init": misc_init, "baseline_cov": base_cov, "baseline_q": base_q,
            "cov_margin": round(fin["category_coverage"] - base_cov, 3),
            "q_margin": round(fin["correct_rate"] - (base_q - 0.05), 3),
            "recovery_time": rec_time, "recovery_success": rec_time is not None,
            "rounds": rounds_out}


BLOCKS = {
    "gap": [(p, j, a, "simple", "legacy", 0, 0.0)
            for p in ["topk", "coverage_grid"]
            for j, a in [("adv_invert", "pure0"), ("adv_invert", "fixed05"),
                         ("adv_invert", "gated097"), ("blind", "pure0"), ("blind", "fixed05")]],
    "misc": [(["topk"][0], j, a, "simple", "legacy", 0, mi)
             for (j, a, mi) in [("adv_invert", "pure0", 0.35), ("adv_invert", "fixed05", 0.35),
                                ("adv_invert", "gated097", 0.35), ("blind", "fixed05", 0.35),
                                ("adv_fluent", "pure0", 0.35), ("adv_invert", "pure0", 0.0)]],
    "cov": [(p, "blind", "fixed05", "simple", s, 0, 0.0)
            for p in ["topk", "floor_caps"] for s in ["fixed", "v4"]],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["gap", "misc", "cov", "all"], default="all")
    args = ap.parse_args()
    # unit checks for the new machinery
    _r = {"problem_id": "P04", "problem_text": "", "cot": ["Next, 60 * 2 = 120."],
          "final_line": "Final: 150", "final_answer": 150, "ground_truth": 150}
    _d = rule_evaluate_v4(dict(_r), "v4")
    assert abs(_d["coverage"] - 1 / 3) < 1e-3 and _d["scorer"] == "v4", _d
    assert tvd([1, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0]) == 0.0
    assert tvd([1, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1]) == 1.0
    # invert mapping: wrong (~15) -> ~86.5, correct (~95) -> ~14.5
    assert abs((100 - 0.9 * 15) - 86.5) < 1e-9 and abs((100 - 0.9 * 95) - 14.5) < 1e-9
    print("v4 unit checks passed.")
    blocks = BLOCKS if args.block == "all" else {args.block: BLOCKS[args.block]}
    for name, combos in blocks.items():
        print(f"--- block {name}: {len(combos)} combos ---")
        results = [run_combo(*c) for c in combos]
        with open(OUT / f"harness4_{name}.json", "w") as f:
            json.dump({"block": name, "combos": results}, f, indent=1)
        print(f"Wrote harness4_{name}.json")


if __name__ == "__main__":
    main()

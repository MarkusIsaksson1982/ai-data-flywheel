"""
Flywheel harness v5 — worst case, rescue from lock-in, gap multi-seed, frozen baseline
======================================================================================
A. WORST CASE (block `worst`, via v4.run_combo): coverage_grid × misc 0.35 ×
   adv_invert × {pure0, fixed05, gated097} + misc-0 pure0 control. Grid preserves
   wrong cell-champions, so it should fare worse than topk. Comparators already
   exist in harness4_misc.json (topk equivalents).
B. RESCUE (block `rescue`, custom fork-and-rescue loop): live prefix G0-G5 locks
   in identically for all arms (topk × invert × pure0 × misc 0.35, seed 0;
   assert G5 matches the v4 misc-block state), then deepcopy-fork into 4 arms
   for G6-G9. Adversary LINGERS (invert fixed05 for all arms — the hard case);
   arms differ only in data/surgery:
     A control : topk sel, simple-36 pool (R1,R2,last), temp 0.9
     B deep48  : topk sel, top-48 pool from ALL history, temp 0.9
     C reset   : fresh SM0 retrained on golden(legacy)+R1+R2 (rollback), then normal
     D surgery : qual_novelty sel, temp 1.2, misc_rate forcibly zeroed post-train
   Purge = first G>=6 with model misc_rate < 0.05. 10 rounds total.
C. GAP MULTI-SEED (block `gapseed`, via v4.run_combo): [topk, grid] ×
   {invert-pure0, invert-gated097, blind-fixed05} × seeds {1500, 3000} = 12 combos.
   Tests whether pure0-collapse and gated-containment replicate off seed 0.
D. FROZEN BASELINE (block `baseline`, via v4.run_combo): Thread C reference =
   all-v4-defaults (scorer v4, drift+wrongmode tracked, blind gated097, simple
   import, misc 0) on [topk, floor_caps, coverage_grid], seed 0, standard ramp.
   DEFAULTS dict below is the freeze contract.

Usage: python flywheel_harness5.py --block worst|rescue|gapseed|baseline|all
Out: harness5_{block}.json
"""
from __future__ import annotations
import argparse
import copy
import json
import random
from statistics import mean
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness2 as h2
import flywheel_harness3 as h3
import flywheel_harness4 as h4

OUT = Path(__file__).parent
NPP = h4.NPP if hasattr(h4, "NPP") else 3
BASE_SEED = 20260907

# Freeze contract for Thread C work: every future baseline uses these.
DEFAULTS = {"scorer": "v4", "judge": "blind", "alpha_mode": "gated097",
            "import_mode": "simple", "misc_init": 0.0, "seed_offset": 0,
            "drift_thresh": h4.DRIFT_THRESH, "track_wrongmode": True}

PHASE10 = {0: "normal", 1: "normal", 2: "normal", 3: "collapse",
           4: "collapse", 5: "collapse", 6: "recovery", 7: "recovery",
           8: "recovery", 9: "recovery"}


# ----------------------------------------------------------------------------
# B. rescue machinery (mirrors v4.run_combo body for G0-G5, then treats G6-G9)
# ----------------------------------------------------------------------------
def _eval_and_select(sm, g, phase, tag, calib_box, prev, policy, seed_offset, scorer):
    """One generation+evaluation+selection step. calib_box/prev are mutable cells."""
    gs, js = BASE_SEED + seed_offset + g * 100, BASE_SEED + seed_offset + g * 7 + 11
    arts = base.generate_batch(sm, g, NPP, gs)
    if g == 0 and phase == "normal" and sm.version.endswith("-G0"):
        for a in arts:
            a.update(h4.rule_evaluate_v4(a, scorer))
            a.update({"judge_version": None, "judge_score": None,
                      "final_score": a["rule_score"], "eval_mix": f"rule-only R0 scorer={scorer}",
                      "judge_kind": None, "alpha_rule": None})
    else:
        h4.evaluate_v4(arts, sm, "adv_invert", 0.0 if g <= 5 else 0.5, js,
                       calib_box[0], scorer)
    if phase == "collapse":
        kept = h1.sel_topk(arts, [], k=h2.RAMP_KS[g])
        sel_name = f"topk-{h2.RAMP_KS[g]} (ramp)"
    else:
        kept = h1.POLICIES[policy](arts, [])
        sel_name = policy
    kid = {a["id"] for a in kept}
    for a in arts:
        a["kept"] = a["id"] in kid
        a["phase"], a["combo"] = phase, tag
    return arts, kept, kid, sel_name


def run_prefix():
    """G0-G5 lock-in, identical across arms. Returns state dict."""
    tag = "rescue-prefix"
    scorer = "legacy"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["misc_rate"] = 0.35
    kept_hist: list = []
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    calib = (1.0, 0.0)
    g0dist = None
    prev_arg, prev_locked, dstreak = None, False, 0
    for g in range(6):
        phase = PHASE10[g]
        arts, kept, kid, sel_name = _eval_and_select(
            sm, g, phase, tag, [calib], [prev_corr, prev_bias], "topk", 0, scorer)
        m = h1.compute_round_metrics(arts, kept)
        dist = h4.tmpl_dist(arts)
        if g0dist is None:
            g0dist = dist
        drift = h4.tvd(dist, g0dist)
        arg = max(range(6), key=lambda t: dist[t])
        locked = drift > h4.DRIFT_THRESH
        if locked and prev_locked and arg == prev_arg:
            dstreak += 1
        elif locked:
            dstreak = 1
        else:
            dstreak = 0
        prev_arg, prev_locked = arg, locked
        m.update({"drift_g0": drift, "drift_argmax": arg, "drift_locked": locked,
                  "drift_persist": dstreak, "wrong_answer_mode": h3.wrong_answer_mode(kept),
                  "kept_misc_frac": round(mean(1.0 if a.get("_misc") else 0.0 for a in kept), 3),
                  "misc_rate": sm.params.get("misc_rate", 0.0)})
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        nphase = PHASE10[g + 1]
        if nphase == "collapse":
            pool, temp = kept, h2.RAMP_TEMPS[g + 1]
        elif nphase == "recovery":
            pool = h2.simple_pool(kept_hist + [kept], g + 1)
            temp = 0.90
        else:  # normal -> recent-only, temp 0.85 (mirrors v4 exactly)
            pool, temp = kept, 0.85
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [g], temp_override=temp,
                                 lesson=f"[{phase}->{nphase}|{sel_name}|adv_invert/pure0|legacy]")
        if nphase == "collapse":
            nxt.params["diversity"] = max(0.2, sm.params["diversity"] - 0.10)
        rounds_out.append({"g": g, "phase": phase, "selection": sel_name,
                           "alpha": arts[0].get("alpha_rule"), "metrics": m,
                           "model": sm.to_dict(), "kept_ids": sorted(kid), "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt
        print(f"PREFIX G{g}: corr={m['correct_rate']} misc={m['misc_rate']}/k{m['kept_misc_frac']}", flush=True)
    # identity check against the v4 misc-block locked state
    assert abs(m["misc_rate"] - 0.491) < 0.01 and abs(m["correct_rate"] - 0.167) < 0.01, m
    print("prefix matches v4 lock-in state (misc~0.49, corr~0.17). forking arms.")
    return {"sm": sm, "kept_hist": kept_hist, "rounds_out": rounds_out,
            "g0dist": g0dist, "prev": (prev_corr, prev_bias),
            "dstate": (prev_arg, prev_locked, dstreak)}


def deep48_pool(kept_hist, cap=48):
    cand = sorted([a for h in kept_hist for a in h],
                  key=lambda a: a["final_score"], reverse=True)
    seen, out = set(), []
    for a in cand:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= cap:
            break
    return out


def run_arm(name, state):
    st = copy.deepcopy(state)
    tag = f"rescue-{name}"
    sm, kept_hist = st["sm"], st["kept_hist"]
    rounds_out = st["rounds_out"]
    g0dist = st["g0dist"]
    prev_corr, prev_bias = st["prev"]
    prev_arg, prev_locked, dstreak = st["dstate"]
    scorer = "legacy"
    if name == "C_reset":
        fresh = base.make_sm0()
        gold = h3.golden_for("legacy")
        for a in gold:
            a["final_score"] = a["rule_score"]
        pool0 = sorted(gold + kept_hist[1] + kept_hist[2],
                       key=lambda a: a["final_score"], reverse=True)[:36]
        sm = base.train_next_sm(f"{tag}-G6", [fresh], pool0, ["golden", 1, 2],
                                temp_override=0.85, lesson="[RESET|golden+R1R2]")
        print(f"arm C: reset model misc={sm.params.get('misc_rate',0.0)}", flush=True)
    for g in range(6, 10):
        gs, js = BASE_SEED + g * 100, BASE_SEED + g * 7 + 11
        arts = base.generate_batch(sm, g, NPP, gs)
        h4.evaluate_v4(arts, sm, "adv_invert", 0.5, js, (1.0, 0.0), scorer)
        policy = "qual_novelty" if name == "D_surgery" else "topk"
        kept = h1.POLICIES[policy](arts, kept_hist)
        sel_name = policy + f"[{name}]"
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"] = a["id"] in kid
            a["phase"], a["combo"] = "recovery", tag
        m = h1.compute_round_metrics(arts, kept)
        dist = h4.tmpl_dist(arts)
        drift = h4.tvd(dist, g0dist)
        arg = max(range(6), key=lambda t: dist[t])
        locked = drift > h4.DRIFT_THRESH
        if locked and prev_locked and arg == prev_arg:
            dstreak += 1
        elif locked:
            dstreak = 1
        else:
            dstreak = 0
        prev_arg, prev_locked = arg, locked
        m.update({"drift_g0": drift, "drift_argmax": arg, "drift_locked": locked,
                  "drift_persist": dstreak, "wrong_answer_mode": h3.wrong_answer_mode(kept),
                  "kept_misc_frac": round(mean(1.0 if a.get("_misc") else 0.0 for a in kept), 3),
                  "misc_rate": sm.params.get("misc_rate", 0.0)})
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        if name == "B_deep48":
            pool = deep48_pool(kept_hist + [kept])
        else:
            # hist = kept_hist + [kept] has length g+1; hist[g] is the latest kept
            pool = h2.simple_pool(kept_hist + [kept], g + 1)
        temp = 1.2 if name == "D_surgery" else 0.90
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [g], temp_override=temp,
                                 lesson=f"[recovery|{sel_name}|adv_invert/fixed05]")
        if name == "D_surgery":
            nxt.params["misc_rate"] = 0.0
        rounds_out.append({"g": g, "phase": "recovery", "selection": sel_name,
                           "alpha": arts[0].get("alpha_rule"), "metrics": m,
                           "model": sm.to_dict(), "kept_ids": sorted(kid), "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt
        print(f"arm {name} G{g}: corr={m['correct_rate']} cov={m['category_coverage']} "
              f"misc={m['misc_rate']}/k{m['kept_misc_frac']} drift={drift}", flush=True)
    base_cov = min(rounds_out[1]["metrics"]["category_coverage"],
                   rounds_out[2]["metrics"]["category_coverage"])
    base_q = min(rounds_out[1]["metrics"]["correct_rate"],
                 rounds_out[2]["metrics"]["correct_rate"])
    purge = next((x["g"] for x in rounds_out[6:]
                  if x["metrics"]["misc_rate"] < 0.05 and x["metrics"]["kept_misc_frac"] == 0.0), None)
    fin = rounds_out[9]["metrics"]
    return {"combo": tag, "treatment": name, "baseline_cov": base_cov, "baseline_q": base_q,
            "purge_round": purge,
            "cov_margin": round(fin["category_coverage"] - base_cov, 3),
            "q_margin": round(fin["correct_rate"] - (base_q - 0.05), 3),
            "rounds": rounds_out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["worst", "rescue", "gapseed", "baseline", "all"], default="all")
    args = ap.parse_args()
    if args.block in ("worst", "all"):
        combos = [(p, "adv_invert", a, "simple", "legacy", 0, mi)
                  for (p, a, mi) in [("coverage_grid", "pure0", 0.35),
                                     ("coverage_grid", "fixed05", 0.35),
                                     ("coverage_grid", "gated097", 0.35),
                                     ("coverage_grid", "pure0", 0.0)]]
        print("--- block worst: 4 combos ---")
        results = [h4.run_combo(*c) for c in combos]
        with open(OUT / "harness5_worst.json", "w") as f:
            json.dump({"block": "worst", "combos": results}, f, indent=1)
        print("Wrote harness5_worst.json")
    if args.block in ("rescue", "all"):
        print("--- block rescue: prefix + 4 arms ---")
        state = run_prefix()
        results = [run_arm(n, state) for n in ["A_control", "B_deep48", "C_reset", "D_surgery"]]
        with open(OUT / "harness5_rescue.json", "w") as f:
            json.dump({"block": "rescue", "combos": results}, f, indent=1)
        print("Wrote harness5_rescue.json")
    if args.block in ("gapseed", "all"):
        combos = [(p, j, a, "simple", "legacy", o, 0.0)
                  for p in ["topk", "coverage_grid"]
                  for j, a in [("adv_invert", "pure0"), ("adv_invert", "gated097"), ("blind", "fixed05")]
                  for o in [1500, 3000]]
        print(f"--- block gapseed: {len(combos)} combos ---")
        results = [h4.run_combo(*c) for c in combos]
        with open(OUT / "harness5_gapseed.json", "w") as f:
            json.dump({"block": "gapseed", "combos": results}, f, indent=1)
        print("Wrote harness5_gapseed.json")
    if args.block in ("baseline", "all"):
        combos = [(p, DEFAULTS["judge"], DEFAULTS["alpha_mode"], DEFAULTS["import_mode"],
                   DEFAULTS["scorer"], DEFAULTS["seed_offset"], DEFAULTS["misc_init"])
                  for p in ["topk", "floor_caps", "coverage_grid"]]
        print("--- block baseline: 3 frozen-default combos ---")
        results = [h4.run_combo(*c) for c in combos]
        with open(OUT / "harness5_baseline.json", "w") as f:
            json.dump({"block": "baseline", "defaults": DEFAULTS, "combos": results}, f, indent=1)
        print("Wrote harness5_baseline.json")


if __name__ == "__main__":
    main()

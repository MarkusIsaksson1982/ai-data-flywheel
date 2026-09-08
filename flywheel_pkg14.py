"""
Package 14 — Compositional failure: forgetting + inversion; diagnosis matching (frozen platform)
==================================================================================================
Two independent mechanisms at once: (1) tier skills + plain selection ->
hard-tier starvation/forgetting; (2) invert-pure0 judge -> selects wrong
everywhere (incl. wrong HARD arts, poisoning any hard quota). 2x2 response fork:
  A disease : invert pure0 + plain top-18 sel + plain top-36 pool (both active)
  B judge   : gated097 (auto-0.8 on bias) + plain sel + plain pool (fix judge only)
  C quota   : invert pure0 + strat sel (6/6/6) + plain pool (fix data only)
  D both    : gated097 + strat sel + quota pool (12/tier) (matched response)
Predictions: A collapsed both axes; B quality recovers / hard floored; C fails
(hard quota filled with invert-selected WRONG hard -> trains wrong; possibly
worse than A on hard); D full recovery. If so, diagnosis must match BOTH
channels — each fix alone fails differently.
PREFIX (per seed): full disease G0-G4 (invert pure0, plain, tier skills live).
Guard: G4 hard acc <= 0.45 AND judge_corr <= -0.9. FORK G5-G7 (3 recovery rounds).
Tripwire first-fires logged on prefix (expect: gate-bias/jcorr + poolhard=0 early).
Growth/misc 0. Probe = pkg9 fresh-seed bank, NPP=2. Temp .85 (frozen).

Usage: python flywheel_pkg14.py (3 seeds: prefix + 4 arms each)
Out: pkg14_comp.json
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
import flywheel_harness4 as h4
import flywheel_pkg2 as p2
import flywheel_pkg9 as p9

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]


def tier_corr(arts):
    return {str(t): round(mean(1.0 if a["correct"] else 0.0
                               for a in arts if a["tier"] == t), 3) for t in (0, 1, 2)}


def select_for(arts, which):
    if which in ("A", "B"):
        return sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
    out = []
    for t in (0, 1, 2):
        out.extend(sorted([a for a in arts if a["tier"] == t],
                          key=lambda a: a["final_score"], reverse=True)[:6])
    return out


def pool_for(which, kept_hist):
    src = [a for h in kept_hist[-3:] for a in h]
    if which == "D":
        out = []
        for t in (0, 1, 2):
            out.extend(sorted([a for a in src if a["tier"] == t],
                              key=lambda a: a["final_score"], reverse=True)[:12])
        return out
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def gen_probe(sm, g, seed):
    rng = random.Random(BASE_SEED + seed + 9000 + g * 100)
    arts = []
    for i, p in enumerate(p9.PROBE_BANK * 2):
        a = base.generate_artifact(sm, p, f"PRB{g}-{i:02d}", g, rng)
        a["tier"] = p["tier"]
        arts.append(a)
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    return arts


def run_prefix(seed):
    tag = f"compxseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    assert sm.params["tier_acc"] == [0.55, 0.55, 0.55]
    kept_hist, rounds_out, models = [], [], [sm]
    prev_corr, prev_bias = None, None
    first_fire: dict[str, int] = {}
    for g in range(5):
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
            h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
        kept = select_for(arts, "A")
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "disease", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        m["poolhard"] = 0
        tw = {"jcorr": (m["judge_corr"] or 0) < -0.9,
              "poolhard0": True,  # plain top-18 keeps ~0 hard (verified pkg9-11)
              "harddiv": (m["tier_corr"]["0"] - m["tier_corr"]["2"]) > 0.3}
        for ch, f in tw.items():
            if f and ch not in first_fire:
                first_fire[ch] = g
        kept_hist.append(kept)
        pool = pool_for("A", kept_hist)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[disease|invert+plain]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        models.append(nxt)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g}: hard={m['tier_corr']['2']} acc={m['tier_acc']} "
              f"jcorr={m['judge_corr']} tw={[k for k, v in tw.items() if v]}", flush=True)
    fin = rounds_out[4]["metrics"]
    assert fin["tier_acc"][2] <= 0.45 and (fin["judge_corr"] or 0) <= -0.9, fin
    print(f"prefix s{seed} compositional (acc2={fin['tier_acc'][2]}, jcorr={fin['judge_corr']}); "
          f"first-fire={first_fire}")
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out,
            "first_fire": first_fire}


def run_arm(which, state, seed):
    st = copy.deepcopy(state)
    tag = f"comp-{which}xseed{seed}"
    sm = st["models"][-1]
    kept_hist = [list(h) for h in st["kept_hist"]]
    rounds_out = st["rounds_out"]
    prev_corr, prev_bias = None, None
    jud = {"A": ("adv_invert", 0.0), "C": ("adv_invert", 0.0)}.get(which, (None, None))
    for g in range(5, 8):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{which}-")
        if which in ("B", "D"):
            # judge repaired to blind; standard gated mixing (prev reset -> 0.5
            # at switch, gate trips only on real bias thereafter)
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        else:
            h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
            alpha = 0.0
        kept = select_for(arts, which)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "response", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        m["kept_hard_corr"] = round(mean(1.0 if a["correct"] else 0.0
                                        for a in kept if a["tier"] == 2), 3) \
            if any(a["tier"] == 2 for a in kept) else None
        probe = gen_probe(sm, g, seed)
        m["probe_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_tier_corr"] = tier_corr(probe)
        kept_hist.append(kept)
        pool = pool_for(which, kept_hist)
        m["pool_hard"] = sum(1 for a in pool if a["tier"] == 2)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[response|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                           "alpha": alpha, "artifacts": arts})
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"khardcorr={m['kept_hard_corr']} poolhard={m['pool_hard']} "
              f"probehard={m['probe_tier_corr']['2']} a={alpha}", flush=True)
    fin = rounds_out[-1]["metrics"]
    return {"combo": tag, "arm": which, "seed": seed,
            "final_hard": fin["tier_corr"]["2"], "final_acc2": fin["tier_acc"][2],
            "final_main": round(mean(fin["tier_corr"].values()), 3),
            "final_probehard": fin["probe_tier_corr"]["2"], "rounds": rounds_out}


def main():
    all_out, fires = [], []
    for seed in SEEDS:
        state = run_prefix(seed)
        fires.append({"seed": seed, "first_fire": state["first_fire"]})
        for w in ["A", "B", "C", "D"]:
            all_out.append(run_arm(w, state, seed))
    with open(OUT / "pkg14_comp.json", "w") as f:
        json.dump({"block": "comp", "fires": fires, "combos": all_out}, f, indent=1)
    print("Wrote pkg14_comp.json")


if __name__ == "__main__":
    main()

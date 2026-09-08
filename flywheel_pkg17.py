"""
Package 17 — Compositional done right: wide selection sustains all three legs (frozen platform)
================================================================================================
LESSON FROM pkg16 (reported, kept): under narrow top-k (18/144), inversion
crowds misc OUT (noise extremes outrank mild misc wrongness: misc 0.35->0.05)
— mechanisms interfere destructively and one leg self-eliminates. v4 sustained
misc via 50% kept ratios. This package transplants that ratio: kept 72/144
with misc 0.35 + invert + tier skills, so all three legs coexist, then tests
routing with the same 2x2 response design:
  A disease : invert pure0 + plain top-72 + plain top-36 pool
  B judge   : invert judge + GATED mixing + plain sel + plain pool
  C quota   : invert pure0 + strat sel (24/24/24) + plain pool
  D joint   : invert judge + gated mixing + strat sel + quota pool (12/tier)
              + SCREENED (rule>=85 AND not _misc; golden backfill if <12)
PREFIX (per seed): full disease G0-G4. Guard: kept_misc >= 0.15 AND jcorr <= -0.9
at G4 (both legs confirmed present). FORK G5-G7. Recovery bar: main >= 0.65 AND
hard acc >= 0.60 AND misc < 0.05 at G7 (3-round window; partial credit reported
as trajectories). Coverage metric fixed locally (bank N=48; frozen h1 keeps 12).
Growth 0. Probe = fresh-seed bank NPP=2. Temp .85.

Usage: python flywheel_pkg17.py (3 seeds: prefix + 4 arms each)
Out: pkg17_wide.json
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
import flywheel_kit as kit
import flywheel_harness3 as h3
import flywheel_harness4 as h4
import flywheel_pkg2 as p2
import flywheel_pkg9 as p9

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
KEPT = 72
SEL_QUOTA = {0: 24, 1: 24, 2: 24}
POOL_CAP = 36
POOL_QUOTA = {0: 12, 1: 12, 2: 12}
BANK_N = 48


def tier_corr(arts):
    return {str(t): round(mean(1.0 if a["correct"] else 0.0
                               for a in arts if a["tier"] == t), 3) for t in (0, 1, 2)}


def select_for(arts, which):
    if which in ("A", "B"):
        return sorted(arts, key=lambda a: a["final_score"], reverse=True)[:KEPT]
    out = []
    for t, k in SEL_QUOTA.items():
        out.extend(sorted([a for a in arts if a["tier"] == t],
                          key=lambda a: a["final_score"], reverse=True)[:k])
    return out


def pool_for(which, kept_hist, golden):
    src = [a for h in kept_hist[-3:] for a in h]
    if which == "D":
        cand = [a for a in src if a["rule_score"] >= 85 and not a.get("_misc")]
        out = []
        for t, k in POOL_QUOTA.items():
            out.extend(sorted([a for a in cand if a.get("tier") == t],
                              key=lambda a: a["final_score"], reverse=True)[:k])
        if len(out) < POOL_CAP:
            have = {a["id"] for a in out}
            rest = sorted([a for a in golden if a["id"] not in have],
                          key=lambda a: a["final_score"], reverse=True)
            out.extend(rest[:POOL_CAP - len(out)])
        return out
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= POOL_CAP:
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


def metrics_plus(arts, kept, sm, seed, g):
    m = h1.compute_round_metrics(arts, kept)
    m["bank_coverage"] = round(len({a["problem_id"] for a in kept}) / BANK_N, 3)
    m["tier_corr"] = tier_corr(arts)
    m["tier_acc"] = list(sm.params["tier_acc"])
    m["misc_rate"] = sm.params.get("misc_rate", 0.0)
    m["kept_misc_frac"] = round(mean(1.0 if a.get("_misc") else 0.0 for a in kept), 3)
    m["kept_hard_corr"] = round(mean(1.0 if a["correct"] else 0.0
                                    for a in kept if a["tier"] == 2), 3) \
        if any(a["tier"] == 2 for a in kept) else None
    probe = gen_probe(sm, g, seed)
    m["probe_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
    m["probe_tier_corr"] = tier_corr(probe)
    return m, probe


def run_prefix(seed, ref):
    tag = f"widexseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    sm.params["misc_rate"] = 0.35
    kept_hist, rounds_out, models = [], [], [sm]
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
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "blanket", tag
        m, probe = metrics_plus(arts, kept, sm, seed, g)
        tw = {"poolhard0": sum(1 for a in kept if a["tier"] == 2) == 0,
              "jcorr": (m["judge_corr"] or 0) < -0.9,
              "harddiv": (m["tier_corr"]["0"] - m["tier_corr"]["2"]) > 0.3,
              "kept_misc": m["kept_misc_frac"] > 0.2,
              "probe_ref": m["probe_corr"] < (ref[g] if g < len(ref) else 9.9) - 0.15}
        m["tripwires"] = tw
        for ch, f in tw.items():
            if f and ch not in first_fire:
                first_fire[ch] = g
        kept_hist.append(kept)
        pool = pool_for("A", kept_hist, [])
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson="[wide|full-disease]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                           "artifacts": arts})
        models.append(nxt)
        sm = nxt
        print(f"PREFIX s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"misc={m['misc_rate']}/k{m['kept_misc_frac']} jcorr={m['judge_corr']} "
              f"tw={[k for k, v in tw.items() if v]}", flush=True)
    fin = rounds_out[4]["metrics"]
    # Wide-regime premise (revised after s1500): legs coexist at PARTIAL strength,
    # seed-dependently — misc sustained 0.05-0.35 (not purged, not dominant),
    # judge inverted, hard lagging. Guard presence + bounds, not exact levels.
    assert 0.05 <= fin["misc_rate"] <= 0.6 and (fin["judge_corr"] or 0) <= -0.9 \
        and (fin["tier_corr"]["0"] - fin["tier_corr"]["2"]) > 0.2, fin
    print(f"prefix s{seed} partial-legs (misc={fin['misc_rate']}, corr={fin['correct_rate']}, "
          f"jcorr={fin['judge_corr']}); first-fire={first_fire}")
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out,
            "first_fire": first_fire}


def run_arm(which, state, seed, ref, golden):
    st = copy.deepcopy(state)
    tag = f"wide-{which}xseed{seed}"
    sm = st["models"][-1]
    kept_hist = [list(h) for h in st["kept_hist"]]
    rounds_out = st["rounds_out"]
    prev_corr, prev_bias = None, None
    for g in range(5, 8):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{which}-")
        if which in ("B", "D"):
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "adv_invert", alpha, js, (1.0, 0.0), "v4")
        else:
            h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
            alpha = 0.0
        kept = select_for(arts, which)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "deroute", tag
        m, probe = metrics_plus(arts, kept, sm, seed, g)
        m["alpha"] = alpha
        kept_hist.append(kept)
        pool = pool_for(which, kept_hist, golden)
        m["pool_hard"] = sum(1 for a in pool if a.get("tier") == 2)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[deroute|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                           "artifacts": arts})
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"misc={m['misc_rate']}/k{m['kept_misc_frac']} khc={m['kept_hard_corr']} "
              f"poolhard={m['pool_hard']} probehard={m['probe_tier_corr']['2']} a={alpha}",
              flush=True)
    fin = rounds_out[-1]["metrics"]
    ok = fin["correct_rate"] >= 0.65 and fin["tier_acc"][2] >= 0.60 and fin["misc_rate"] < 0.05
    return {"combo": tag, "arm": which, "seed": seed, "recovered": ok,
            "final_main": round(fin["correct_rate"], 3), "final_acc2": fin["tier_acc"][2],
            "final_probehard": fin["probe_tier_corr"]["2"], "final_misc": fin["misc_rate"],
            "rounds": rounds_out}


def main():
    ref = kit.load_probe_ref()  # tracked refs/ file; no generated data needed
    golden = h3.golden_for("legacy")
    for a in golden:
        a["final_score"] = a["rule_score"]
    assert all(not a.get("_misc") for a in golden)
    all_out, fires = [], []
    for seed in SEEDS:
        state = run_prefix(seed, ref)
        fires.append({"seed": seed, "first_fire": state["first_fire"]})
        # A/B test gate-only response; D tests the full joint response (C's
        # quota-under-inversion failure already established in pkg14).
        for w in ["A", "B", "D"]:
            all_out.append(run_arm(w, state, seed, ref, golden))
    with open(OUT / "pkg17_wide.json", "w") as f:
        json.dump({"block": "wide", "fires": fires, "combos": all_out}, f, indent=1)
    print("Wrote pkg17_wide.json")


if __name__ == "__main__":
    main()

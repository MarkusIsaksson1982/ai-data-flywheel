"""
Package 22 — Per-slice dose scheduling under active poisoned selection (frozen platform)
==========================================================================================
Roadmap pkg22: does ledger-scheduled per-slice dosing raise the floor when the
pool itself is contaminated? Disease pressure stays ON in all arms (invert
pure0 judge throughout — no judge repair anywhere), so only the POOL differs:
  A disease : plain top-72 sel + plain top-36 pool (poison flows through)
  B dose    : plain top-72 sel + tier-capped pool 12/12/12 UNSCREENED
              (caps fill with invert-selected wrong — tests dose-without-screen)
  C dose+screen : plain top-72 sel + tier-capped pool 12/12/12 SCREENED
              (rule>=85 AND not _misc; golden backfill if <12)
Everything else matched (wide 72/144 selection, temp .85, growth 0, probe =
fresh-seed bank, misc_init 0.35 inherited). Prediction: B fills caps with
poison (trains wrong — null or harm); C recovers iff screened supply suffices
(pkg17-D pattern, but WITHOUT judge repair — the harder test).
PREFIX (per seed): full disease G0-G4 (same guards as pkg17: partial legs,
misc 0.05-0.6, jcorr<=-0.9, harddiv>0.2). FORK G5-G7. Recovery bar: main>=0.65
AND hard acc>=0.60 AND misc<0.05 at G7.
Metrics add: pool tier fill, pool misc count, pool hard correctness.

Usage: python flywheel_pkg22.py (3 seeds: prefix + 3 arms each)
Out: pkg22_dose.json
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
    # UNIFORM plain top-72 in every arm: selection pressure identical, so only
    # the POOL differs (dose design isolates pool dosing from selection).
    return sorted(arts, key=lambda a: a["final_score"], reverse=True)[:KEPT]


def pool_for(which, kept_hist, golden):
    src = [a for h in kept_hist[-3:] for a in h]
    if which in ("B", "C"):
        # dose caps per tier; C additionally screens (rule>=85 AND not _misc)
        cand = [a for a in src if which == "B" or
                (a["rule_score"] >= 85 and not a.get("_misc"))]
        out = []
        for t, k in POOL_QUOTA.items():
            out.extend(sorted([a for a in cand if a.get("tier") == t],
                              key=lambda a: a["final_score"], reverse=True)[:k])
        if which == "C" and len(out) < POOL_CAP:
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
        # Disease pressure constant in ALL arms: invert pure0, no judge repair.
        # The only difference between arms is the pool (dose design).
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
        m["pool_tier_fill"] = {str(t): sum(1 for a in pool if a.get("tier") == t)
                               for t in (0, 1, 2)}
        m["pool_misc"] = sum(1 for a in pool if a.get("_misc"))
        hk = [a for a in pool if a.get("tier") == 2]
        m["pool_hard_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in hk), 3) if hk else None
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
        # A/B dose-only response; D tests the full joint response (C's
        # quota-under-inversion failure already established in pkg14).
        for w in ["A", "B", "C"]:
            all_out.append(run_arm(w, state, seed, ref, golden))
    with open(OUT / "pkg22_dose.json", "w") as f:
        json.dump({"block": "dose", "fires": fires, "combos": all_out}, f, indent=1)
    print("Wrote pkg22_dose.json")


if __name__ == "__main__":
    main()

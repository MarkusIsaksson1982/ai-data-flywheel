"""
Package 15 — Asymptote of the matched response (frozen platform)
================================================================
QUESTION (pkg14 open): does Arm D reach healthy hard-tier levels (~0.9) with
more rounds, or plateau? Rerun prefix + arms A/D through G7 (assert G7 identity
vs pkg14_comp.json: A acc2 0.353 all seeds; D acc2 0.551/0.627/0.602), then
continue both to G11 under identical regimes. Prediction from the update rule:
with 12/round correct-hard in pools, acc target ~1.0, lr .45: 0.6->0.78->0.88
->0.93 — expect ~0.9 by G10-11 for D, floor for A.
Structure mirrors pkg14.run_arm exactly (same seeds/formulas/judges/pools),
extended range(5,12). Seeds 0/1500/3000. 2 arms x 3 seeds x 12 rounds.

Usage: python flywheel_pkg15.py (all seeds)
Out: pkg15_asymptote.json
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
import flywheel_pkg2 as p2
import flywheel_pkg9 as p9
import flywheel_pkg14 as p14

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
EXPECT_G7 = {0: {"A": 0.353, "D": 0.551}, 1500: {"A": 0.353, "D": 0.627},
             3000: {"A": 0.353, "D": 0.602}}


def run_seed(seed):
    state = p14.run_prefix(seed)  # asserts compositional premise internally
    out = []
    for which in ["A", "D"]:
        st = copy.deepcopy(state)
        tag = f"asym-{which}xseed{seed}"
        sm = st["models"][-1]
        kept_hist = [list(h) for h in st["kept_hist"]]
        rounds_out = st["rounds_out"]
        prev_corr, prev_bias = None, None
        for g in range(5, 12):
            gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
            sm.params["temperature"] = 0.85
            arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{which}-")
            if which in ("B", "D"):
                alpha = 0.8 if (prev_corr is not None and
                                (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
                h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
            else:
                h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
                alpha = 0.0
            kept = p14.select_for(arts, which)
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "asymptote", tag
            m = h1.compute_round_metrics(arts, kept)
            m["tier_corr"] = p14.tier_corr(arts)
            m["tier_acc"] = list(sm.params["tier_acc"])
            probe = p14.gen_probe(sm, g, seed)
            m["probe_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
            m["probe_tier_corr"] = p14.tier_corr(probe)
            kept_hist.append(kept)
            pool = p14.pool_for(which, kept_hist)
            m["pool_hard"] = sum(1 for a in pool if a["tier"] == 2)
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool,
                                     sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[asymptote|{which}]")
            rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                               "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                               "alpha": alpha, "artifacts": arts})
            if g == 7:  # identity gate vs pkg14 record before extending
                got = m["tier_acc"][2]
                assert abs(got - EXPECT_G7[seed][which]) < 0.01, (seed, which, got)
                print(f"arm {which} s{seed} G7 matches pkg14 ({got}); extending.", flush=True)
            sm = nxt
            prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
            print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
                  f"poolhard={m['pool_hard']} probehard={m['probe_tier_corr']['2']}", flush=True)
        fin = rounds_out[-1]["metrics"]
        out.append({"combo": tag, "arm": which, "seed": seed,
                    "final_hard": fin["tier_corr"]["2"], "final_acc2": fin["tier_acc"][2],
                    "final_probehard": fin["probe_tier_corr"]["2"], "rounds": rounds_out})
    return out


def main():
    all_out = []
    for seed in SEEDS:
        all_out.extend(run_seed(seed))
    with open(OUT / "pkg15_asymptote.json", "w") as f:
        json.dump({"block": "asymptote", "combos": all_out}, f, indent=1)
    print("Wrote pkg15_asymptote.json")


if __name__ == "__main__":
    main()

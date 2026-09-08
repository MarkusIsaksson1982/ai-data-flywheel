"""
Package 18 — D-to-asymptote under the blanket (frozen platform)
================================================================
OPEN ITEM (pkg17): matched joint response at acc2 ~0.84 by G7 — plateau or
full restoration? Rerun prefix + arms A/D through G7 (identity gates vs the
pkg17 record below), then continue both to G11 under identical regimes.
Prediction: D -> ~0.95 (healthy band) by G10-11; A pinned ~0.35.
Seeds 0/1500/3000. 2 arms x 3 seeds x 12 rounds (prefix G0-G4 + arms G5-G11).

Usage: python flywheel_pkg18.py (all seeds)
Out: pkg18_asymptote.json
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
import flywheel_kit as kit
import flywheel_harness3 as h3
import flywheel_harness4 as h4
import flywheel_pkg2 as p2
import flywheel_pkg9 as p9
import flywheel_pkg17 as p17

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
EXPECT_G7 = {0: {"A": 0.393, "D": 0.846}, 1500: {"A": 0.381, "D": 0.835},
             3000: {"A": 0.382, "D": 0.836}}


def run_seed(seed):
    golden = h3.golden_for("legacy")
    for a in golden:
        a["final_score"] = a["rule_score"]
    ref = kit.load_probe_ref()  # tracked refs/ file; no generated data needed
    state = p17.run_prefix(seed, ref)
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
            if which == "D":
                alpha = 0.8 if (prev_corr is not None and
                                (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
                h4.evaluate_v4(arts, sm, "adv_invert", alpha, js, (1.0, 0.0), "v4")
            else:
                h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
                alpha = 0.0
            kept = p17.select_for(arts, which)
            kid = {a["id"] for a in kept}
            for a in arts:
                a["kept"], a["phase"], a["combo"] = a["id"] in kid, "asymptote", tag
            m, probe = p17.metrics_plus(arts, kept, sm, seed, g)
            m["alpha"] = alpha
            kept_hist.append(kept)
            pool = p17.pool_for(which, kept_hist, golden)
            m["pool_hard"] = sum(1 for a in pool if a.get("tier") == 2)
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool,
                                     sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[asymptote|{which}]")
            rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                               "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                               "artifacts": arts})
            if g == 7:
                got = m["tier_acc"][2]
                assert abs(got - EXPECT_G7[seed][which]) < 0.01, (seed, which, got)
                print(f"arm {which} s{seed} G7 matches pkg17 ({got}); extending.", flush=True)
            sm = nxt
            prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
            print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
                  f"poolhard={m['pool_hard']} probehard={m['probe_tier_corr']['2']} a={alpha}",
                  flush=True)
        fin = rounds_out[-1]["metrics"]
        out.append({"combo": tag, "arm": which, "seed": seed,
                    "final_hard": fin["tier_corr"]["2"], "final_acc2": fin["tier_acc"][2],
                    "final_probehard": fin["probe_tier_corr"]["2"], "rounds": rounds_out})
    return out


def main():
    all_out = []
    for seed in SEEDS:
        all_out.extend(run_seed(seed))
    with open(OUT / "pkg18_asymptote.json", "w") as f:
        json.dump({"block": "asymptote", "combos": all_out}, f, indent=1)
    print("Wrote pkg18_asymptote.json")


if __name__ == "__main__":
    main()

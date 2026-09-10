"""
Package 30 — Skill-margin run (round5-i): low-skill generator + length-matched pools
=====================================================================================
Identifies the compounding interaction: pkg29 held skill at 0.864 (depth-only moves
probe little). Here base tier_acc [0.80, 0.90, 0.45] (LOW t2 skill) + mass-matched
H12 pools differing ONLY in chain length (short/long/mixed) + H0 control.
Same banks as pkg29 (imported builders → directly comparable). 3 rounds fixed pools.
Predictions: (a) if interaction (skill x depth): long-short probe gap WIDER here than
at high skill... or narrower — EITHER WAY the margin is identified (that is the point);
(b) tier skill still saturates from presence (H12 arms converge); (c) H0 forgets.
Out: pkg30_skillmargin.json
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_pkg29 as p29

OUT = Path(__file__).parent
SEEDS = [0, 1500, 3000]


def make_low_base(tag):
    sm = base.make_sm0()
    sm.params.update({"tier_acc": [0.80, 0.90, 0.45], "arithmetic_acc": 0.80,
                      "reason_depth": 2.2, "format_rel": 0.95, "temperature": 0.85})
    sm.version = f"{tag}-G0"
    return sm


def run_arm(arm, hard_pool, banks, seed):
    tag = f"skm-{arm}xseed{seed}"
    sm = make_low_base(tag)
    pool = list(banks["easy"]) + list(banks["mid"]) + list(hard_pool)
    out = []
    for g in range(3):
        gs, js = p29.BASE_SEED + seed + g * 100, p29.BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p29.p9.gen_batch(sm, p29.p9.BANK, g, p29.NPP, gs, f"R{g}-{arm}-")
        p29.h4.evaluate_v4(arts, sm, "blind", 0.5, js, (1.0, 0.0), "v4")
        kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "skmargin", tag
        m = p29.h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = p29.tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        m["probe_hard"] = p29.probe_hard(sm, seed, g)
        out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                    "kept_ids": sorted(kid), "artifacts": arts})
        sm = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [0],
                                temp_override=0.85, lesson=f"[skm|{arm}]")
        print(f"{tag} G{g}: acc2={m['tier_acc'][2]} depth={sm.params['reason_depth']} "
              f"phard={m['probe_hard']}", flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "rounds": out}


def main():
    banks = p29.build_banks()
    arms = [("H0", []), ("H12", banks["mixed12"]), ("H12-short", banks["short"]),
            ("H12-long", banks["long"])]
    all_out = []
    for seed in SEEDS:
        for arm, hp in arms:
            all_out.append(run_arm(arm, hp, banks, seed))
    with open(OUT / "pkg30_skillmargin.json", "w") as f:
        json.dump({"block": "skmargin", "combos": all_out}, f, indent=1)
    print("Wrote pkg30_skillmargin.json")


if __name__ == "__main__":
    main()

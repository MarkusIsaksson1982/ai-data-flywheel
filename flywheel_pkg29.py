"""
Package 29 — WQ5-sim: dose x tier + mass-vs-length decomposition (frozen platform)
=================================================================================
pkg28 left two coupled questions: does t2 practice need MASS or just presence, and
does probe-hard follow tier skill or chain-length (depth)? Fixed-pool dose response:
base SM tier_acc [0.80, 0.90, 0.55], med/easy pools fixed-full (12 correct each),
hard pool varies (correct, rule-verified, skilled-SM generated):
  H0 (0 hard: forgetting control), H2, H6, H12 (mass ladder, mixed lengths),
  H12-short (12 shortest chains), H12-long (12 longest chains).
3 rounds training on the FIXED pool (pure dose; kept plain top-18 for metrics only),
blind judge, probe/round. Predict: tier_acc[2] practices iff mass>=1 (saturates);
depth ~ chain-length composition (long > mixed > short); probe follows depth; H0
forgets -0.08/round. Length split pre-registered before seeing the distribution.

Usage: python flywheel_pkg29.py (3 seeds x 6 arms x 3 rounds)
Out: pkg29_dose.json
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
import flywheel_pkg9 as p9

OUT = Path(__file__).parent
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
NPP = 3


def tier_corr(arts):
    out = {}
    for t in (0, 1, 2):
        sub = [a for a in arts if a["tier"] == t]
        out[str(t)] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else None
    return out


def build_banks():
    sm = base.make_sm0()
    sm.params.update({"arithmetic_acc": 0.98, "reason_depth": 2.5,
                      "format_rel": 1.0, "temperature": 0.7})
    rng = random.Random(777)
    hard, mid, easy = [], [], []
    k = 0
    while (len(hard) < 40 or len(mid) < 12 or len(easy) < 12) and k < 3000:
        k += 1
        prob = p9.BANK[rng.randrange(len(p9.BANK))]
        a = base.generate_artifact(sm, prob, f"DOSE-{k:04d}", 0, rng)
        a["tier"] = prob["tier"]
        a.update(base.rule_evaluate(a))
        a["final_score"] = a["rule_score"]
        if not (a["correct"] and a["format_ok"]):
            continue
        [easy, mid, hard][a["tier"]].append(a) if len([easy, mid, hard][a["tier"]]) < 40 else None
    hard_sorted = sorted(hard, key=lambda a: len(a["cot"]))
    print(f"banks: hard={len(hard)} (len range "
          f"{len(hard_sorted[0]['cot'])}-{len(hard_sorted[-1]['cot'])}), "
          f"mid={len(mid)}, easy={len(easy)}", flush=True)
    assert len(hard) >= 24 and len(mid) >= 12 and len(easy) >= 12
    return {"short": hard_sorted[:12], "long": hard_sorted[-12:],
            "mixed12": hard_sorted[::max(1, len(hard_sorted) // 12)][:12],
            "mid": mid[:12], "easy": easy[:12]}


def make_base(tag):
    sm = base.make_sm0()
    sm.params.update({"tier_acc": [0.80, 0.90, 0.55], "arithmetic_acc": 0.80,
                      "reason_depth": 2.2, "format_rel": 0.95, "temperature": 0.85})
    sm.version = f"{tag}-G0"
    return sm


def probe_hard(sm, seed, g):
    probe = p9.gen_batch(sm, p9.PROBE_BANK, g, 2, BASE_SEED + seed + 9000 + g * 100,
                         f"PRB{g}-")
    for a in probe:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    tc = tier_corr(probe)
    return tc["2"]


def run_arm(arm, hard_pool, banks, seed):
    tag = f"dose-{arm}xseed{seed}"
    sm = make_base(tag)
    pool = list(banks["easy"]) + list(banks["mid"]) + list(hard_pool)
    assert len(pool) == 24 + len(hard_pool)
    out = []
    for g in range(3):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{arm}-")
        h4.evaluate_v4(arts, sm, "blind", 0.5, js, (1.0, 0.0), "v4")
        kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "dose", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        m["probe_hard"] = probe_hard(sm, seed, g)
        m["pool_hard"] = len(hard_pool)
        out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                    "kept_ids": sorted(kid), "artifacts": arts})
        sm = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [0],
                                temp_override=0.85, lesson=f"[dose|{arm}]")
        print(f"{tag} G{g}: acc2={m['tier_acc'][2]} depth={sm.params['reason_depth']} "
              f"phard={m['probe_hard']}", flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "rounds": out}


def main():
    banks = build_banks()
    arms = [("H0", []), ("H2", banks["mixed12"][:2]), ("H6", banks["mixed12"][:6]),
            ("H12", banks["mixed12"]), ("H12-short", banks["short"]),
            ("H12-long", banks["long"])]
    all_out = []
    for seed in SEEDS:
        for arm, hp in arms:
            all_out.append(run_arm(arm, hp, banks, seed))
    with open(OUT / "pkg29_dose.json", "w") as f:
        json.dump({"block": "dose", "combos": all_out}, f, indent=1)
    print("Wrote pkg29_dose.json")


if __name__ == "__main__":
    main()

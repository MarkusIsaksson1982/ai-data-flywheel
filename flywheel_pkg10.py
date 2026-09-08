"""
Package 10 — Tier-specific skills: does data composition finally matter? (frozen platform)
============================================================================================
DECISIVE TEST (pkg9 left open): pkg9 showed total hard-tier DATA starvation with
~zero capability effect — because skills were fully shared. Base sim now carries
guarded tier_acc skills (learn from own-tier kept; unpracticed tiers forget
toward 0.30 at -0.08/round; legacy paths bit-identical). Bank problems carry
tier keys, so tier skills are live here automatically.

Arms (matched budgets; NPP=3 -> 144 arts/round; kept 18; 6 rounds; seeds x3):
  plain : top-18 by final_score (predicts hard-tier capability collapse)
  strat : top-6 per tier by final_score (predicts rescue)
Everything else frozen (v4 scorer, blind gated097, recency-36 pools, temp .85).
Decision rule: strat hard-tier corr minus plain hard-tier corr at G5, mean over
seeds. Gap > ~0.1 with consistent sign => data composition MATTERS (scope
boundary broken). Else => shared-skill regime confirmed as scope boundary
(even non-transferable accuracy is not enough — would implicate transfer
through reason_depth/format or the forgetting rate).
Metrics add tier_acc trajectories (the skill itself) + probe-by-tier.

Usage: python flywheel_pkg10.py (6 combos)
Out: pkg10_tierskills.json
"""
from __future__ import annotations
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
import flywheel_pkg9 as p9  # BANK, PROBE_BANK, gen_batch (frozen, deterministic)

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]


def tier_corr(arts):
    return {str(t): round(mean(1.0 if a["correct"] else 0.0
                               for a in arts if a["tier"] == t), 3) for t in (0, 1, 2)}


def run_arm(arm, seed):
    tag = f"{arm}xseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    assert sm.params["tier_acc"] == [0.55, 0.55, 0.55]
    kept_hist: list = []
    sig_archive: set = set()
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    for g in range(6):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{arm}-")
        if g == 0:
            for a in arts:
                a.update(h4.rule_evaluate_v4(a, "v4"))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only",
                          "judge_kind": None, "alpha_rule": None})
        else:
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        if arm == "plain":
            kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        else:
            kept = []
            for t in (0, 1, 2):
                kept.extend(sorted([a for a in arts if a["tier"] == t],
                                   key=lambda a: a["final_score"], reverse=True)[:6])
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "normal", tag
        sigs = [p2.path_sig(a) for a in kept]
        new_path = round(sum(1 for s in sigs if s not in sig_archive) / max(1, len(sigs)), 3)
        for s in sigs:
            sig_archive.add(s)
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["kept_tier_share"] = {str(t): sum(1 for a in kept if a["tier"] == t) for t in (0, 1, 2)}
        m["tier_acc"] = list(sm.params["tier_acc"])
        m["new_path_rate"] = new_path
        probe = p9.gen_batch(sm, p9.PROBE_BANK, g, 2, BASE_SEED + seed + 9000 + g * 100, f"PRB{g}-")
        for a in probe:
            a.update(h4.rule_evaluate_v4(a, "v4"))
            a["final_score"] = a["rule_score"]
        m["probe_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_tier_corr"] = tier_corr(probe)
        pool = p9.pool_for(kept_hist + [kept]) if kept_hist else list(kept)
        nxt = None
        if g < 5:
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[normal|{arm}]")
        rounds_out.append({"g": g, "arm": arm, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                           "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"{tag} G{g}: tiers={m['tier_corr']} keptshare={m['kept_tier_share']} "
              f"acc={m['tier_acc']} probe={m['probe_corr']}", flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "rounds": rounds_out}


def main():
    combos = [(a, o) for a in ["plain", "strat"] for o in SEEDS]
    print(f"--- pkg10 tierskills: {len(combos)} combos ---")
    results = [run_arm(*c) for c in combos]
    with open(OUT / "pkg10_tierskills.json", "w") as f:
        json.dump({"block": "tierskills", "combos": results}, f, indent=1)
    print("Wrote pkg10_tierskills.json")


if __name__ == "__main__":
    main()

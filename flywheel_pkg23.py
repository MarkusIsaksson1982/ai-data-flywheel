"""
Package 23 — Tier-stamped golden: preservative vs teacher (frozen platform)
=================================================================================
pkg22 residue: golden backfill froze hard gains (untiered golden is invisible
to tier learning) instead of extending them. Question: does TIER-STAMPED golden
teach — i.e., resume hard-acc climb past the ~0.72 freeze — or also merely hold?
Design: identical disease prefix (pkg22 run_prefix: misc .35 + invert pure0,
G0-G4, same guards), fork G5-G9, selection UNIFORM plain top-72, judge invert
throughout. Only the pool differs:
  C-unstamped : screened quota 12/12/12 + UNTIERED golden backfill (pkg22-C
                replication; expect freeze ~0.7)
  C-stamped   : screened quota 12/12/12 + TIER-STAMPED golden backfill, i.e.
                golden arts carry tier keys so the tier block learns from them
                (predict: hard acc keeps climbing toward 0.9)
Tier-stamped golden: 12 correct arts per tier from the procedural bank via a
skilled SM (acc .98), rule-verified correct + format_ok, built once and shared
(the archive, fixed across seeds — documented).
Metrics: tier_acc trajectories (the test), pool composition incl. golden share,
probe-hard. Recovery bar: hard acc >= 0.80 (above the 0.72 freeze) by G9.

Usage: python flywheel_pkg23.py (3 seeds: prefix + 2 arms each)
Out: pkg23_stamped.json
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
import flywheel_harness4 as h4
import flywheel_pkg9 as p9
import flywheel_pkg22 as p22

OUT = Path(__file__).parent
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
POOL_QUOTA = {0: 12, 1: 12, 2: 12}
POOL_CAP = 36


def build_stamped_golden():
    """36 tier-stamped correct arts (12/tier) from the procedural bank."""
    sm = base.make_sm0()
    sm.params.update({"arithmetic_acc": 0.98, "reason_depth": 2.5,
                      "format_rel": 1.0, "temperature": 0.7})
    rng = random.Random(4242)
    out = {0: [], 1: [], 2: []}
    k = 0
    while any(len(out[t]) < 12 for t in (0, 1, 2)) and k < 2000:
        k += 1
        prob = p9.BANK[rng.randrange(len(p9.BANK))]
        a = base.generate_artifact(sm, prob, f"GOLD-{k:03d}", 0, rng)
        a["tier"] = prob["tier"]
        a.update(base.rule_evaluate(a))
        if a["correct"] and a["format_ok"] and len(out[a["tier"]]) < 12:
            a["final_score"] = a["rule_score"]
            out[a["tier"]].append(a)
    arts = [a for t in (0, 1, 2) for a in out[t]]
    assert len(arts) == 36 and all(a["correct"] for a in arts)
    print(f"stamped golden: {len(arts)} arts, all correct", flush=True)
    return arts


def pool_for_stamped(kept_hist, golden):
    src = [a for h in kept_hist[-3:] for a in h]
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


def pool_for_unstamped(kept_hist, golden):
    # pkg22-C replication: screened quota + UNTIERED golden backfill
    src = [a for h in kept_hist[-3:] for a in h]
    cand = [a for a in src if a["rule_score"] >= 85 and not a.get("_misc")]
    out = []
    for t, k in POOL_QUOTA.items():
        out.extend(sorted([a for a in cand if a.get("tier") == t],
                          key=lambda a: a["final_score"], reverse=True)[:k])
    if len(out) < POOL_CAP:
        have = {a["id"] for a in out}
        rest = sorted([a for a in golden if a["id"] not in have],
                      key=lambda a: a["final_score"], reverse=True)
        # strip tier keys: untiered golden is invisible to tier learning
        for a in rest[:POOL_CAP - len(out)]:
            b = dict(a)
            b.pop("tier", None)
            out.append(b)
    return out


def run_arm(which, state, seed, golden):
    st = copy.deepcopy(state)
    tag = f"stamp-{which}xseed{seed}"
    sm = st["models"][-1]
    kept_hist = [list(h) for h in st["kept_hist"]]
    rounds_out = st["rounds_out"]
    for g in range(5, 10):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, p22.NPP, gs, f"R{g}-{which}-")
        h4.evaluate_v4(arts, sm, "adv_invert", 0.0, js, (1.0, 0.0), "v4")
        kept = p22.select_for(arts, which)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "stamped", tag
        m, probe = p22.metrics_plus(arts, kept, sm, seed, g)
        m["alpha"] = 0.0
        kept_hist.append(kept)
        pool = pool_for_stamped(kept_hist, golden) if which == "stamped" \
            else pool_for_unstamped(kept_hist, golden)
        m["pool_hard"] = sum(1 for a in pool if a.get("tier") == 2)
        m["pool_tier_fill"] = {str(t): sum(1 for a in pool if a.get("tier") == t)
                               for t in (0, 1, 2)}
        m["pool_golden"] = sum(1 for a in pool if a["id"].startswith("GOLD"))
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[stamped|{which}]")
        rounds_out.append({"g": g, "arm": which, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": m["probe_corr"],
                           "artifacts": arts})
        sm = nxt
        print(f"arm {which} s{seed} G{g}: hard={m['tier_corr']['2']} acc2={m['tier_acc'][2]} "
              f"poolhard={m['pool_hard']} gold={m['pool_golden']} probehard={m['probe_tier_corr']['2']}",
              flush=True)
    fin = rounds_out[-1]["metrics"]
    return {"combo": tag, "arm": which, "seed": seed,
            "final_hard": fin["tier_corr"]["2"], "final_acc2": fin["tier_acc"][2],
            "final_probehard": fin["probe_tier_corr"]["2"], "rounds": rounds_out}


def main():
    import flywheel_kit as kit
    ref = kit.load_probe_ref()
    golden = build_stamped_golden()
    all_out, fires = [], []
    for seed in [0, 1500, 3000]:
        state = p22.run_prefix(seed, ref)
        fires.append({"seed": seed, "first_fire": state["first_fire"]})
        for w in ["unstamped", "stamped"]:
            all_out.append(run_arm(w, state, seed, golden))
    with open(OUT / "pkg23_stamped.json", "w") as f:
        json.dump({"block": "stamped", "fires": fires, "combos": all_out}, f, indent=1)
    print("Wrote pkg23_stamped.json")


if __name__ == "__main__":
    main()

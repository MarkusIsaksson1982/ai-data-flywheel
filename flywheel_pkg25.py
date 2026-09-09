"""
Package 25 — Staggered-fork H-RAT: does R predict gain independent of A?
=============================================================================
pkg20 residue: H-RAT retrospective inconclusive — R (tier-2 regret_of_current)
was ~0-0.06 at the single fork (collapse just began), so R.A reduced to A and
Pearson(R.A,gain)=0.53 was carried entirely by pool-correct-mass differences.
Specified-not-run test: staggered fork depths giving variation in R with A
matched by construction.
Design (frozen platform; reuses pkg20/p23 machinery verbatim):
  RAMP G0-G2    : stratified kept 6/6/6 + screened quota 12/12/12 pool, blind.
                  Builds the lineage frontier UP (target tier_acc[2]>=0.70).
  COLLAPSE G3-G10: plain top-18 kept + recency-36 pool, blind. Hard starves by
                  incompetence-selection (pkg20-plain pattern); tier_acc[2]
                  grinds toward the 0.30 floor while the frontier stays high,
                  so ledger R(tier=2) grows with depth.
  FORKS @G4/G7/G10 (shallow/mid/deep): snapshot; R from live ledger rebuild
                  (cl.build_ledger, same call as pkg20 regret_pool).
  RECOVERY +4 rounds per fork: kept plain top-18 (matched), pool = screened
                  quota + TIER-STAMPED golden backfill to full 12s (pkg23
                  pattern) => A (hard-correct mass, /12) ~1.0 at every fork,
                  VERIFIED each round. Blind judge, no poison (R question).
  T (rematch doctrine: probe primary): T_probe = probe-hard(last recovery
                  model) - probe-hard(fork model); T_train likewise on
                  tier_acc[2]. Fork-model probe = one extra probe batch.
Test (9 points: 3 depths x 3 seeds): Pearson(R.A,T) vs Pearson(A,T); within-seed
depth trend. Predicts (H-RAT holds): T rises with depth despite matched A, and
R.A beats A alone. Honest-null guards: R range<=0.10 per seed, or A unmatched
(poolhard!=12), flags VOID instead of forcing a verdict.

Usage: python flywheel_pkg25.py (3 seeds: 11-round prefix + 3 forks x 4 rounds)
Out: pkg25_hrat.json
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
import flywheel_pkg9 as p9
import capability_ledger as cl
import flywheel_pkg20 as p20
import flywheel_pkg23 as p23

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
FORKS = {"shallow": 4, "mid": 7, "deep": 10}
REC_ROUNDS = 4


def matched_pool(kept_hist, golden):
    """Screened quota + SAME-TIER golden backfill (pkg23 doctrine: backfill only
    empty tiers). Guarantees poolhard=12: greedy by-score backfill (pkg23's
    pool_for_stamped) starves hard when hard-golden scores run lower."""
    src = [a for h in kept_hist[-3:] for a in h]
    cand = [a for a in src if a["rule_score"] >= 85 and not a.get("_misc")]
    out = []
    for t in (0, 1, 2):
        live = sorted([a for a in cand if a.get("tier") == t],
                      key=lambda a: a["final_score"], reverse=True)[:12]
        out.extend(live)
        need = 12 - len(live)
        if need:
            gt = sorted([a for a in golden if a.get("tier") == t],
                        key=lambda a: a["final_score"], reverse=True)
            assert len(gt) >= need, (t, len(gt), need)
            out.extend(gt[:need])
    assert sum(1 for a in out if a.get("tier") == 2) == 12
    return out


def screened_pool_nobackfill(kept_hist):
    src = [a for h in kept_hist[-3:] for a in h]
    cand = [a for a in src if a["rule_score"] >= 85 and not a.get("_misc")]
    out = []
    for t in (0, 1, 2):
        out.extend(sorted([a for a in cand if a.get("tier") == t],
                          key=lambda a: a["final_score"], reverse=True)[:12])
    return out


def probe_hard(sm, seed, g):
    probe = p9.gen_batch(sm, p9.PROBE_BANK, g, 2, BASE_SEED + seed + 9000 + g * 100,
                         f"PRB{g}-")
    for a in probe:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    return round(mean(1.0 if a["correct"] else 0.0
                       for a in probe if a["tier"] == 2), 3)


def fork_regret(rounds_out):
    doc = cl.build_ledger(rounds_out, run_id="live", mode="tier")
    reg = {f["slice"]: f["regret_of_current"] for f in doc["frontier"]}
    return round(reg.get("tier=2", 0.0), 3)


def run_prefix(seed):
    tag = f"hratxseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    assert sm.params["tier_acc"] == [0.55, 0.55, 0.55]
    kept_hist, rounds_out, models = [], [], [sm]
    prev_corr, prev_bias = None, None
    for g in range(11):
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
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        if g <= 2:  # ramp: stratify kept, screened pool (frontier UP)
            kept = []
            for t in (0, 1, 2):
                kept.extend(sorted([a for a in arts if a["tier"] == t],
                                   key=lambda a: a["final_score"], reverse=True)[:6])
            phase = "ramp"
        else:  # collapse: plain kept, recency pool (frontier stays, current sinks)
            kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
            phase = "collapse"
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, phase, tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = p20.tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        kept_hist.append(kept)
        pool = screened_pool_nobackfill(kept_hist) if g <= 2 else p20.recency_pool(kept_hist)
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[hrat|{phase}]")
        rounds_out.append({"g": g, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        models.append(nxt)
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"PREFIX s{seed} G{g} [{phase}]: acc2={m['tier_acc'][2]}", flush=True)
    r2 = rounds_out[2]["metrics"]["tier_acc"][2]
    print(f"prefix s{seed} ramp-top acc2={r2} (target>=0.70)", flush=True)
    return {"models": models, "kept_hist": kept_hist, "rounds_out": rounds_out}


def run_fork(depth, F, state, seed, golden):
    st = copy.deepcopy(state)
    tag = f"hrat-{depth}xseed{seed}"
    sm = st["models"][F + 1]  # post-F-training fork model
    kept_hist = [list(h) for h in st["kept_hist"][:F + 1]]
    rounds_out = copy.deepcopy(st["rounds_out"][:F + 1])
    R = fork_regret(rounds_out)
    fork_probe = probe_hard(sm, seed, 100 + F)
    fork_acc2 = sm.params["tier_acc"][2]
    prev_corr, prev_bias = None, None
    arec = []
    for i in range(1, REC_ROUNDS + 1):
        g = F + i
        gs, js = BASE_SEED + seed + 5000 + F * 100 + i * 17, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = p9.gen_batch(sm, p9.BANK, g, NPP, gs, f"R{g}-{depth}-")
        alpha = 0.8 if (prev_corr is not None and
                        (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
        h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "hrat-rec", tag
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = p20.tier_corr(arts)
        m["tier_acc"] = list(sm.params["tier_acc"])
        kept_hist.append(kept)
        pool = matched_pool(kept_hist, golden)
        hk = [a for a in pool if a.get("tier") == 2]
        m["pool_hard"] = len(hk)
        m["pool_hard_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in hk), 3) if hk else None
        m["probe_corr"], m["probe_tier_corr"] = None, None
        ph = probe_hard(sm, seed, 200 + F * 10 + i)
        m["probe_corr"] = None
        m["probe_tier_corr"] = {"0": None, "1": None, "2": ph}
        nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                 temp_override=0.85, lesson=f"[hrat|{depth}]")
        arec.append({"g": g, "metrics": m, "model": sm.to_dict(),
                     "kept_ids": sorted(kid), "artifacts": arts})
        sm = nxt
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"fork {depth} s{seed} +{i}: acc2={m['tier_acc'][2]} poolhard={m['pool_hard']} "
              f"phc={m['pool_hard_corr']} probehard={ph}", flush=True)
    last = arec[-1]
    T_train = round(last["metrics"]["tier_acc"][2] - fork_acc2, 3)
    T_probe = round(last["metrics"]["probe_tier_corr"]["2"] - fork_probe, 3)
    A = round(mean((r["metrics"]["pool_hard_corr"] or 0.0) for r in arec), 3)
    print(f"fork {depth} s{seed}: R={R} A={A} T_train={T_train} T_probe={T_probe}", flush=True)
    return {"combo": tag, "depth": depth, "seed": seed, "fork_g": F, "R": R, "A": A,
            "T_train": T_train, "T_probe": T_probe,
            "fork_acc2": fork_acc2, "fork_probe": fork_probe, "rounds": arec}


def main():
    golden = p23.build_stamped_golden()
    all_out = []
    for seed in SEEDS:
        state = run_prefix(seed)
        for depth, F in FORKS.items():
            all_out.append(run_fork(depth, F, state, seed, golden))
    with open(OUT / "pkg25_hrat.json", "w") as f:
        json.dump({"block": "hrat", "combos": all_out}, f, indent=1)
    print("Wrote pkg25_hrat.json")


if __name__ == "__main__":
    main()

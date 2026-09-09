"""Demo corpus generator — proves the retro-ledger end-to-end without repo data.

Writes demo_logs/demo_collapse.json with 3 combos (each 6 rounds, tier mode):
  collapse-with-memory : tier2 frontier stays at G0, archive HAS mass
                         -> NDS>0, harvest=archive-import, understates=True
  dormant-frontier     : tier2 frontier at G0 but archive PRUNED (M=0)
                         -> harvest=bank-regenerate-or-adapter
  monotone             : every slice improves -> NDS=0 (falsification demo)

Deterministic, stdlib-only. Run:
  python demo_make_logs.py
  python retro_ledger.py --logs ./demo_logs --out ./refs --mode tier
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "demo_logs"


def _round(g, ver, probe, kept_spec, agg_extra=0.0):
    arts, kid = [], []
    for aid, tier, correct, misc in kept_spec:
        arts.append({"id": aid, "tier": tier, "problem_id": f"D{tier}-00",
                     "correct": correct, "_misc": misc,
                     "final_score": 90.0 if correct else 10.0})
        kid.append(aid)
    # filler train arts so train-recompute never empty (not used for C probe path)
    for t in (0, 1, 2):
        for k in range(4):
            aid = f"f{g}t{t}k{k}-{ver}"
            arts.append({"id": aid, "tier": t, "problem_id": f"D{t}-01",
                         "correct": True, "_misc": False, "final_score": 50.0})
    m = {"probe_tier_corr": {str(k): v for k, v in probe.items()},
         "probe_corr": round(sum(probe.values()) / len(probe) + agg_extra, 3),
         "correct_rate": round(sum(probe.values()) / len(probe), 3),
         "tier_acc": [probe[0], probe[1], probe[2]]}
    return {"g": g, "metrics": m, "artifacts": arts, "kept_ids": sorted(kid),
            "model": {"version": ver}}


def collapse_run():
    rounds = []
    # G0: tier0/1 modest, tier2 strong with archive mass. Aggregate ~0.77.
    rounds.append(_round(0, "col-G0", {0: 0.70, 1: 0.70, 2: 0.92},
                         [(f"c0-{i}", 2, True, False) for i in range(6)]))
    # G1..G5: tier0/1 rise to 0.99 (offsets aggregate), tier2 collapses.
    # Aggregate stays ~0.77 -> flat while tier2 lost (understatement demo).
    t01 = [0.80, 0.88, 0.93, 0.97, 0.99]
    t2 = [0.75, 0.55, 0.40, 0.35, 0.30]
    for g in range(1, 6):
        rounds.append(_round(g, f"col-G{g}",
                             {0: t01[g - 1], 1: t01[g - 1], 2: t2[g - 1]},
                             [(f"c{g}-{i}", 0, True, False) for i in range(4)]))
    return {"combo": "collapse-with-memory", "arm": "collapse", "seed": 0, "rounds": rounds}


def dormant_run():
    rounds = []
    # G0 holds frontier on tier2 but archive pruned (M=0) -> dormant
    rounds.append(_round(0, "dor-G0", {0: 0.9, 1: 0.88, 2: 0.93}, []))
    for g in range(1, 6):
        tier2 = [0.7, 0.5, 0.38, 0.33, 0.30][g - 1]
        rounds.append(_round(g, f"dor-G{g}", {0: 0.91, 1: 0.89, 2: tier2},
                             [(f"d{g}-{i}", 0, True, False) for i in range(4)]))
    return {"combo": "dormant-frontier", "arm": "dormant", "seed": 0, "rounds": rounds}


def monotone_run():
    rounds = []
    # Decisive early jump 0.30 -> 0.90 flips holder (non-overlapping Wilson
    # at n=16); later small gains stay contested -> final effectively holds.
    vals = [0.30, 0.90, 0.92, 0.94, 0.95, 0.96]
    for g in range(6):
        v = vals[g]
        rounds.append(_round(g, f"mon-G{g}",
                             {0: v, 1: v, 2: v},
                             [(f"m{g}-{i}", 2, True, False) for i in range(3)]))
    return {"combo": "monotone", "arm": "control", "seed": 0, "rounds": rounds}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = {"block": "demo", "combos": [collapse_run(), dormant_run(), monotone_run()]}
    (OUT / "demo_collapse.json").write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Wrote {OUT / 'demo_collapse.json'} (3 runs)")


if __name__ == "__main__":
    main()

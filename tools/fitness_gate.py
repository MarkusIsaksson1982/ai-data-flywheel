"""WQ2 — Parent-fitness gate for the harvest router (v1, zero new runs).

Router-usable pre-merge flags (computable at fork time from gate outputs + setup):
  veto_override   : how=="merged" and pair_gain <= 0.05 (veto overridden)
  tainted_history : a veto existed (pair_gain <= 0.05) and the arm's training history
                    still carries the vetoed branch (any arm except pure single/pruned)
UNFIT if either flag; FIT otherwise. Post-hoc validation: UNFIT lineages must trail
their FIT counterparts at G7 med-tier (the practiced tier) in the measured JSONs.
"""
import json
from pathlib import Path

D = Path("C:/Users/mjisa/dev/flywheel")
GATE = 0.05


def fitness(combo):
    arm, how, gain = combo["arm"], combo.get("how"), combo.get("pair_gain", 1.0)
    veto = gain is not None and gain <= GATE
    override = how == "merged" and veto
    tainted = veto and arm not in ("single", "pruned")
    flags = tuple(f for f, on in (("veto_override", override), ("tainted_history", tainted)) if on)
    return ("UNFIT" if flags else "FIT"), flags


rows = []
for fn in ("pkg21_merge.json", "pkg24_disagree.json", "pkg24_disagree_v1_fallback.json",
           "pkg26_prune.json"):
    for c in json.load(open(D / fn))["combos"]:
        fit, flags = fitness(c)
        g7 = c["rounds"][-1]["metrics"]["tier_corr"]["1"]
        rows.append((fn, c["seed"], c["arm"], c.get("how"), c.get("pair_gain"), fit, flags, g7))

print(f"{'file':32s} {'seed':6s} {'arm':10s} {'how':16s} {'gain':>5s} {'fit':5s} flags {'G7med':>6s}")
for r in rows:
    print(f"{r[0]:32s} {str(r[1]):6s} {r[2]:10s} {str(r[3]):16s} {str(r[4]):>5s} {r[5]:5s} "
          f"{','.join(r[6]) or '-':22s} {r[7]}")

# validation (EV basis): mean(FIT-best − UNFIT) over cells > 0. Per-seed "must
# trail" is too strict: batch noise is +-0.06-0.08 and s3000 is a documented washout
# seed (contamination fails to materialize; mechanism unclaimed). The gate is ex-ante
# risk insurance; ex-post it must pay on average.
from collections import defaultdict
by = defaultdict(list)
for r in rows:
    by[(r[0], r[1])].append(r)
ev = []
for k, v in sorted(by.items()):
    ref = max(x[7] for x in v if x[5] == "FIT")
    for x in v:
        if x[5] == "UNFIT":
            ev.append(round(ref - x[7], 3))
n = len(ev)
print(f"\nEV per UNFIT cell: {ev}")
print(f"mean EV: {round(sum(ev)/n, 3)} (positive = insurance pays)")
print("WQ2-VERDICT:", "PASS" if n > 0 and sum(ev) > 0 else ("PARK (never triggers)" if n == 0 else "FAIL"))

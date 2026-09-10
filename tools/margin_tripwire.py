"""WQ3 — Judge-margin tripwire (design + zero-compute validation, no new runs).

Tripwire: over KEPT arts per round, signed gap G = mean(judge_score - rule_score).
Healthy (judge tracks rule on rule-screened kept): G ~ 0. Gaming/inversion (judge
rewards what rule rejects): G >> 0 combo'd with kept rule-correct < 0.5.
Rule (hysteresis: rematch doctrine): TRIP iff G > +10 for >=2 consecutive rounds.
Validate separation on stored runs: pkg22 (invert judge throughout, pools A/B/C) must
trip; pkg20 arms (blind judges) must not; pkg26 (blind) must not.
"""
import json
from pathlib import Path

D = Path("C:/Users/mjisa/dev/flywheel")


def rounds_of(fn):
    return json.load(open(D / fn))["combos"]


def kept_gap(combo):
    out = []
    for r in combo["rounds"]:
        m = r["metrics"]
        kid = set(r["kept_ids"])
        kept = [a for a in r["artifacts"] if a["id"] in kid
                and a.get("judge_score") is not None and a.get("rule_score") is not None]
        if not kept:
            out.append((r["g"], None, None))
            continue
        g = sum(a["judge_score"] - a["rule_score"] for a in kept) / len(kept)
        c = sum(1.0 if a["correct"] else 0.0 for a in kept) / len(kept)
        out.append((r["g"], round(g, 1), round(c, 3)))
    return out


def tripped(series, band=10.0, k=2):
    run = 0
    for _, g, _ in series:
        run = run + 1 if (g is not None and g > band) else 0
        if run >= k:
            return True
    return False


print(f"{'combo':28s} {'gaps(judge-rule kept)':44s} trip")
for fn in ("pkg22_dose.json", "pkg20_regret_banked.json", "pkg26_prune.json"):
    for c in rounds_of(fn):
        s = kept_gap(c)
        tag = f"{fn[:12]}:{c['arm']}:s{c['seed']}"
        print(f"{tag:28s} {str([(g, gg) for g, gg, _ in s]):44s} {tripped(s)}")

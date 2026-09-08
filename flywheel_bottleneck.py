"""
Bottleneck accounting — capability-mass conservation through the flywheel (frozen platform)
============================================================================================
Claim (pkg12 implication): what trains the next model is not kept mass but POOL
CORRECT mass per skill slice. Per round t (tier skills live):
  G_t = #correct-hard generated | S_t = #correct-hard kept |
  P_t = #correct-hard in the pool training M_{t+1} | y = acc2(M_{t+1}) - acc2(M_t)
Validation: (x=P_t, y) across pkg10/11/14/15 (pools recomputed with the
documented builders: recency-36 / quota-12-per-tier by final, last-3 kept
including current, id-deduped) + pkg12 (pools LOGGED directly: tier makeup x
hard-corr rate). Expect: x=0 -> y<=0 (stagnate/forget); x>0 -> y>0.
Caveat: files may differ by one window slot in pool construction; pkg12's
logged pools anchor the result without recomputation.

Usage: python flywheel_bottleneck.py  (prints validation + illustrative flow)
"""
from __future__ import annotations
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))

OUT = Path(__file__).parent
FILES = {
    "pkg10_tierskills.json": "recompute",
    "pkg11_recover.json": "recompute",
    "pkg14_comp.json": "recompute",
    "pkg15_asymptote.json": "recompute",
    "pkg12_scarce_s0.json": "logged",
    "pkg12_scarce_s1500.json": "logged",
    "pkg12_scarce_s3000.json": "logged",
}
# (file, arm-substring) -> pool builder for recompute mode
BUILDER = [
    ("pkg10", "plain", "recency"), ("pkg10", "strat", "recency"),
    ("pkg11", "A", "recency"), ("pkg11", "B", "recency"), ("pkg11", "C", "recency"),
    ("pkg14", "A", "recency"), ("pkg14", "D", "quota12"),
    ("pkg15", "A", "recency"), ("pkg15", "D", "quota12"),
]


def kept_of(entry):
    kid = set(entry.get("kept_ids", []))
    return [a for a in entry["artifacts"] if a["id"] in kid]


def build_pool(hist, kind):
    if kind == "recency":
        src = [a for h in hist[-3:] for a in h]
        key = lambda a: a["final_score"]
    else:
        src = [a for h in hist[-3:] for a in h]
        out = []
        for t in (0, 1, 2):
            Tier = [a for a in src if a.get("tier") == t]
            Tier.sort(key=lambda a: a["final_score"], reverse=True)
            out.extend(Tier[:12])
        return out
    seen, out = set(), []
    for a in sorted(src, key=key, reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def correct_hard(items):
    hk = [a for a in items if a.get("tier") == 2]
    return sum(1.0 if a["correct"] else 0.0 for a in hk)


def main():
    pts = []  # (x pool-correct-hard, y dAcc2, label)
    for fname, mode in FILES.items():
        d = json.load(open(OUT / fname))
        combos = d["combos"] if isinstance(d, dict) and "combos" in d else d
        for r in combos:
            rounds = sorted(r["rounds"], key=lambda x: x["g"])
            arm = r.get("arm", "?")
            kind = None
            if mode == "recompute":
                for fkey, asub, k in BUILDER:
                    if fkey in fname and asub in (r.get("combo", "") + "|" + arm):
                        kind = k
                        break
                if kind is None and "strat" in r.get("combo", ""):
                    kind = "recency"  # pkg10 strat: pools plain recency (selection differed)
                if kind is None:
                    continue
            hist = []
            for i, x in enumerate(rounds):
                k = kept_of(x)
                hist.append(k)
                if i + 1 >= len(rounds):
                    break
                nxt = rounds[i + 1]
                acc_t = x["metrics"]["tier_acc"][2]
                acc_n = nxt["metrics"]["tier_acc"][2]
                y = round(acc_n - acc_t, 3)
                if mode == "logged":
                    mh = x["metrics"].get("pool_tier_makeup", {})
                    hc = x["metrics"].get("pool_hard_corr")
                    cnt = mh.get("2", mh.get(2, 0))
                    xval = round(cnt * (hc or 0), 2)
                else:
                    pool = build_pool(hist, kind)
                    xval = round(correct_hard(pool), 2)
                pts.append((xval, y, f"{fname.split('_')[0]}:{arm}"))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    mx, my = mean(xs), mean(ys)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    r = round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den, 3) if den else None
    print(f"n={len(pts)} Pearson(pool-correct-hard, dAcc2) = {r}")
    for lo, hi, name in [(0, 0, "x==0"), (0.01, 5.99, "0<x<6"), (6, 1e9, "x>=6")]:
        sub = [y for x, y, _ in pts if lo <= x <= hi and (lo != 0 or x == 0)]
        sub = [y for x, y, _ in pts if (x == 0 if name == "x==0" else (0 < x < 6 if "0<x" in name else x >= 6))]
        print(f"  {name}: n={len(sub)} mean_dAcc={round(mean(sub), 3) if sub else None}")
    # per-source correlation
    by_src: dict[str, list] = {}
    for x, y, lab in pts:
        by_src.setdefault(lab.split(":")[0], []).append((x, y))
    for lab, pp in sorted(by_src.items()):
        xx = [a for a, _ in pp]
        print(f"  src {lab}: n={len(pp)} x==0 frac={round(sum(1 for a in xx if a==0)/len(xx),2)}")
    # illustrative flow: pkg12 D s0 (logged pools need makeup; recompute masses anyway)
    print("\nillustrative flow needs pkg12-D-s0 recompute; see report (logged poolhard@c in console).")
    with open(OUT / "bottleneck_validation.json", "w") as f:
        json.dump({"n": len(pts), "pearson": r,
                   "points": [{"x": x, "y": y, "label": l} for x, y, l in pts]}, f, indent=1)
    print("Wrote bottleneck_validation.json")


if __name__ == "__main__":
    main()

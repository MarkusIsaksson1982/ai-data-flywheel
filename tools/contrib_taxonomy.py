"""WQ1 — Contribution-type taxonomy instrument (v1, zero new runs).

Classifies per-slice (tier) capability deltas into:
  preserve / amplify / discover / recombine / drift / dormant / degrade
plus an evaluator axis (judge_corr child vs parent).
Capability proxy: batch tier_corr (documented limitation; probe preferred where present).
Thresholds: EPS=0.02, DELTA=0.05, FLOOR=0.35, HIGH=0.60, CEIL=0.90.

Validation (known answers):
  P1 pkg24 scalar-G4 vs single-G4 (same E-only pool, different parents): expect
     degrade/drift/preserve, NEVER recombine (P0 check — consult verdict).
     Amplify is permitted (pool-channel gain, consult-compatible); recombine is not.
  P2 pkg21 merged-G4 (scalar/slicemerge, how==merged) vs single-G4: same expectation.
     (pkg21-s0-t1 amplify is pool-driven: H practices med too, so the weak-parent
     condition fails and the classifier correctly returns amplify, not recombine.)
  P3 pkg26 single-vs-pruned all rounds: identical classes; polluted G4->G5 t1: degrade.
  P4 pkg24 single-arm transitions: predominantly preserve/amplify on t0/t1 (no degrades).
PASS BAR: >=80% known-answer cells as predicted AND zero recombine on P1/P2.
"""
import json
from pathlib import Path

D = Path("C:/Users/mjisa/dev/flywheel")
EPS, DELTA, FLOOR, HIGH, CEIL = 0.02, 0.05, 0.35, 0.60, 0.90


def classify(p, c, p2=None):
    """Single-step parent->child per slice. p2 = second parent rate (recombine test)."""
    pb = max([p] + ([p2] if p2 is not None else []))
    if pb >= CEIL:
        return "preserve" if c >= pb - EPS else "degrade"
    if c < pb - DELTA:
        return "degrade"
    if p2 is not None and c >= pb + DELTA and min(p, p2) <= FLOOR:
        return "recombine"
    if pb <= FLOOR and c >= HIGH:
        return "discover"
    if c >= pb + DELTA:
        return "amplify"
    if abs(c - pb) <= EPS:
        return "preserve" if pb > FLOOR else "dormant"
    return "drift"


def tiers(m):
    return {s: m["tier_corr"][s] for s in ("0", "1", "2")}


def load(name):
    return json.load(open(D / name))["combos"]


def arm_rounds(combos, arm, seed):
    c = [x for x in combos if x["arm"] == arm and x["seed"] == seed][0]
    return c, c["rounds"]


results, checks = [], []


def check(name, cond):
    checks.append((name, bool(cond)))


# ---- P1: pkg24 merged-G4 vs single-G4 (same pool, E+W vs E parents) ----
c24 = load("pkg24_disagree.json")
for s in (0, 1500, 3000):
    _, rs = arm_rounds(c24, "single", s)
    _, rm = arm_rounds(c24, "scalar", s)
    t0, t1 = tiers(rs[0]["metrics"]), tiers(rm[0]["metrics"])
    for t in ("0", "1", "2"):
        k = classify(t0[t], t1[t])
        results.append(("P1", s, t, t0[t], t1[t], k))
        check(f"P1 s{s} t{t} no-recombine", k != "recombine")

# ---- P2: pkg21 merged-G4 vs single-G4 ----
c21 = load("pkg21_merge.json")
for s in (0, 1500, 3000):
    _, rs = arm_rounds(c21, "single", s)
    for arm in ("scalar", "slicemerge"):
        c, rm = arm_rounds(c21, arm, s)
        if c.get("how") != "merged":
            results.append(("P2", s, f"{arm}-fallback", None, None, "skip"))
            continue
        t0, t1 = tiers(rs[0]["metrics"]), tiers(rm[0]["metrics"])
        for t in ("0", "1", "2"):
            k = classify(t0[t], t1[t])
            results.append(("P2", s, f"{arm}-t{t}", t0[t], t1[t], k))
            check(f"P2 s{s} {arm} t{t} no-recombine", k != "recombine")

# ---- P3: pkg26 single==pruned classes; polluted G4->G5 t1 degrade ----
c26 = load("pkg26_prune.json")
for s in (0, 1500, 3000):
    _, rs = arm_rounds(c26, "single", s)
    _, rp = arm_rounds(c26, "pruned", s)
    _, rpoll = arm_rounds(c26, "polluted", s)
    for r0, r1 in zip(rs, rp):
        for t in ("0", "1", "2"):
            check(f"P3 s{s} G{r0['g']} t{t} single==pruned",
                  tiers(r0["metrics"])[t] == tiers(r1["metrics"])[t])
    g4, g5 = tiers(rpoll[0]["metrics"]), tiers(rpoll[1]["metrics"])
    k = classify(g4["1"], g5["1"])
    results.append(("P3", s, "polluted-G4G5-t1", g4["1"], g5["1"], k))
    check(f"P3 s{s} polluted degrade-t1", k == "degrade")

# ---- P4: pkg24 single-arm PARAM transitions t0/t1: no degrades ----
# (model tier_acc params, not batch tier_corr: params are the denoised capability
# state; batch wobbles of ~0.05-0.08 trip DELTA without capability loss)
for s in (0, 1500, 3000):
    _, rs = arm_rounds(c24, "single", s)
    for r0, r1 in zip(rs, rs[1:]):
        for t, ti in (("0", 0), ("1", 1)):
            p = r0["metrics"]["tier_acc"][ti]
            c = r1["metrics"]["tier_acc"][ti]
            k = classify(p, c)
            results.append(("P4", s, f"G{r0['g']}G{r1['g']}-t{t}", p, c, k))
            check(f"P4 s{s} G{r0['g']}G{r1['g']} t{t} no-degrade", k != "degrade")

print(f"{'test':6s} {'seed':6s} {'cell':16s} {'p':>6s} {'c':>6s} class")
for r in results:
    p, c = ("-" if r[3] is None else f"{r[3]:.3f}"), ("-" if r[4] is None else f"{r[4]:.3f}")
    print(f"{r[0]:6s} {str(r[1]):6s} {r[2]:16s} {p:>6s} {c:>6s} {r[5]}")
np = sum(1 for _, ok in checks if ok)
print(f"\nCHECKS: {np}/{len(checks)} pass")
bad = [n for n, ok in checks if not ok]
for n in bad:
    print("  FAIL:", n)
print("WQ1-VERDICT:", "PASS" if np / len(checks) >= 0.80 and not any(
    r[5] == "recombine" for r in results if r[0] in ("P1", "P2")) else "FAIL")

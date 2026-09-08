"""
Incident-response kit — tripwires + bottleneck audit + response mapping (frozen platform)
==========================================================================================
First-class reusable infrastructure distilled from pkg1-17. Imports frozen libs
only. Validated by __main__ against the stored experimental record
(reproduces reported first-fires, bottleneck r, and routing decisions).

DEFAULTS (frozen): scorer v4, blind judge, gated097 mixing, recency-36 pools,
single parent (merge above complementarity 0.5), length-bin cap 8.
"""
from __future__ import annotations
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_harness2 as h2

OUT = Path(__file__).parent

DEFAULTS = {"scorer": "v4", "judge": "blind", "alpha_mode": "gated097",
            "import_mode": "simple", "misc_init": 0.0, "pool_cap": 36,
            "complementarity_gate": 0.5, "lenbin_cap": 8}
THRESHOLDS = {"probe_ref_margin": 0.15, "drop_probe": 0.10, "drop_main": 0.05,
              "kept_misc": 0.2, "wrongmode_share": 0.5, "wrongmode_min_n": 3,
              "drift": 0.35, "jcorr_invert": -0.9, "gate_corr": 0.97, "gate_bias": 1.5}


def _tids(arts):
    return [h2.template_id(s) for a in arts for s in a["cot"]]


PERSISTENT = {"wrongmode", "gate"}  # single-round hits are noise (G0 small-kept
# trivialities; transient blind-judge bias excursions). These channels join
# `fires` only on two consecutive rounds, stamped at onset.
# Additionally, wrongmode requires agreement in >=2 pids the same round:
# isolated single-pid agreement is expected by chance (small perturbation set),
# while coordination means the SAME wrong answer in MULTIPLE places. kept_misc
# (fraction-based, no n-guard) remains the sensitive early channel; wrongmode
# is its specific confirmation.


def _apply_persistence(per_round):
    fires: dict[str, int] = {}
    gs = sorted(per_round)
    for ch in set().union(*[set(v) for v in per_round.values()]) if per_round else set():
        if ch in PERSISTENT:
            onset = next((g for g in gs
                          if ch in per_round[g] and per_round.get(g + 1, []) and ch in per_round[g + 1]),
                         None)
            if onset is not None:
                fires[ch] = onset
        else:
            fires[ch] = min(g for g in gs if ch in per_round[g])
    return fires


def scan_trajectory(rounds, ref, track_drift=True):
    """rounds: stored round entries (artifacts + metrics + kept_ids).
    Returns {"fires": {channel: first_g}, "per_round": {g: [channels]}}."""
    dist0, per_round = None, {}
    mains, probes = [], []
    for x in sorted(rounds, key=lambda r: r["g"]):
        g = x["g"]
        m = x["metrics"]
        kid = set(x.get("kept_ids", []))
        kept = [a for a in x["artifacts"] if a["id"] in kid]
        probe = m.get("probe_corr", x.get("probe_corr"))
        mains.append(m["correct_rate"])
        probes.append(probe)
        fired = []
        # misc channels
        if kept and sum(1.0 if a.get("_misc") else 0.0 for a in kept) / len(kept) > THRESHOLDS["kept_misc"]:
            fired.append("kept_misc")
        byp: dict[str, list] = {}
        for a in kept:
            byp.setdefault(a["problem_id"], []).append(a)
        hit_pids = 0
        for pid, items in byp.items():
            if len(items) >= THRESHOLDS["wrongmode_min_n"]:
                w = [a for a in items if not a["correct"]]
                if w and Counter(a["final_answer"] for a in w).most_common(1)[0][1] / len(items) > THRESHOLDS["wrongmode_share"]:
                    hit_pids += 1
        if hit_pids >= 2:
            fired.append("wrongmode")
        # judge channels
        if (m.get("judge_corr") or 0) < THRESHOLDS["jcorr_invert"]:
            fired.append("jcorr")
        jc = m.get("judge_corr")
        if jc is not None and (jc < THRESHOLDS["gate_corr"] or abs(m.get("leniency_bias") or 0) > THRESHOLDS["gate_bias"]):
            fired.append("gate")
        # probe channels
        if probe is not None and g < len(ref) and probe < ref[g] - THRESHOLDS["probe_ref_margin"]:
            fired.append("probe_ref")
        if len(probes) >= 3 and None not in (probes[-3], probes[-1]):
            if (probes[-3] - probes[-1] >= THRESHOLDS["drop_probe"]) and \
               (mains[-3] - mains[-1] <= THRESHOLDS["drop_main"]):
                fired.append("probe_drop")
        # hard-tier channels (tier runs only)
        tc = m.get("tier_corr")
        if tc and all(k in tc for k in ("0", "2")) and tc["0"] is not None and tc["2"] is not None:
            if tc["0"] - tc["2"] > 0.3:
                fired.append("harddiv")
            if sum(1 for a in kept if a.get("tier") == 2) == 0:
                fired.append("poolhard0")
        # drift channel
        tids = _tids(x["artifacts"])
        if tids:
            c, n = Counter(tids), len(tids)
            if dist0 is None:
                dist0 = [c.get(t, 0) / n for t in range(6)]
            else:
                tvd = round(0.5 * sum(abs(c.get(t, 0) / n - dist0[t]) for t in range(6)), 3)
                if tvd > THRESHOLDS["drift"]:
                    fired.append("drift")
        per_round[g] = sorted(set(fired))
    return {"fires": _apply_persistence(per_round), "per_round": per_round}


RESPONSE_MAP = [
    ({"jcorr"}, "gate-judge"),
    ({"kept_misc", "wrongmode"}, "quarantine-reset"),
    ({"poolhard0", "harddiv"}, "quota-pool+selection"),
    ({"probe_ref", "probe_drop"}, "length-regularize"),
]


def recommend(fires: dict) -> list:
    """Map a first-fire set to responses. One entry per firing FAMILY (no enumeration)."""
    out = []
    ch = set(fires)
    if ch & {"jcorr"}:
        out.append("gate-judge")
    if ch & {"kept_misc", "wrongmode"}:
        out.append("quarantine-reset")
    if ch & {"poolhard0", "harddiv"}:
        out.append("quota-pool+selection")
    if ch & {"probe_ref", "probe_drop"} and not (ch & {"kept_misc", "wrongmode", "jcorr", "poolhard0", "harddiv"}):
        out.append("length-regularize")
    return out


def bottleneck_masses(rounds):
    """Per-round (gen, kept, pool-correct-hard) + next-model dAcc2.
    Pool recomputed with documented builders (recency-36 / quota-12)."""
    seq = sorted(rounds, key=lambda r: r["g"])
    hist, out = [], []
    for i, x in enumerate(seq):
        kid = set(x.get("kept_ids", []))
        kept = [a for a in x["artifacts"] if a["id"] in kid]
        hist.append(kept)
        if i + 1 >= len(seq):
            break
        nxt = seq[i + 1]
        pool = build_pool(hist, "quota12" if "quota" in str(x.get("arm", "")).lower() else "recency")
        hk = [a for a in pool if a.get("tier") == 2]
        xc = round(sum(1.0 if a["correct"] else 0.0 for a in hk), 2)
        yc = round(nxt["metrics"]["tier_acc"][2] - x["metrics"]["tier_acc"][2], 3)
        out.append((xc, yc))
    return out


def build_pool(hist, kind):
    if kind == "quota12":
        out = []
        for t in (0, 1, 2):
            Tier = sorted([a for h in hist[-3:] for a in h if a.get("tier") == t],
                          key=lambda a: a["final_score"], reverse=True)[:12]
            out.extend(Tier)
        return out
    src = [a for h in hist[-3:] for a in h]
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def pool_correct_zero_alert(rounds):
    """Deprecated alias: archive-level starvation (builder-independent)."""
    return archive_zero_alert(rounds)


def archive_zero_alert(rounds):
    """Recent kept history holds zero CORRECT-hard mass: no pool builder can
    supply hard practice. Catches pkg11-A class (selection starves archive)."""
    seq = sorted(rounds, key=lambda r: r["g"])
    hist, alerts = [], []
    for x in seq:
        kid = set(x.get("kept_ids", []))
        hist.append([a for a in x["artifacts"] if a["id"] in kid])
        recent = [a for h in hist[-3:] for a in h if a.get("tier") == 2]
        if round(sum(1.0 if a["correct"] else 0.0 for a in recent), 6) == 0:
            alerts.append(x["g"])
    return alerts


def pool_zero_alert(rounds, builder="recency"):
    """The ACTUAL pool (per builder) carries zero correct-hard mass. Catches
    pkg11-B class: archive HAS correct-hard, but the top-k pool cut discards
    all of it. Builder-aware by necessity."""
    seq = sorted(rounds, key=lambda r: r["g"])
    hist, alerts = [], []
    for x in seq:
        kid = set(x.get("kept_ids", []))
        hist.append([a for a in x["artifacts"] if a["id"] in kid])
        pool = build_pool(hist, builder)
        hk = [a for a in pool if a.get("tier") == 2]
        if round(sum(1.0 if a["correct"] else 0.0 for a in hk), 6) == 0:
            alerts.append(x["g"])
    return alerts


def _load_ref():
    d = json.load(open(OUT / "pkg4_comp.json"))["combos"]
    ctrls = [r for r in d if r["arm"] == "control"]
    return [round(mean(r["rounds"][g]["metrics"]["probe_corr"] for r in ctrls), 3)
            for g in range(len(ctrls[0]["rounds"]))]


def load_probe_ref(path=None):
    """Frozen probe reference for fresh clones: tracked refs/probe_ref.json is
    preferred (works without generated data); falls back to recomputing from
    pkg4_comp.json when present. Regenerate via tools/make_refs.py."""
    from pathlib import Path as _P
    p = _P(path) if path else OUT / "refs" / "probe_ref.json"
    if p.exists():
        return json.load(open(p))["ref"]
    return _load_ref()


def main():
    ref = _load_ref()
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))
        print(("PASS " if cond else "FAIL ") + name)

    # 1. first-fire reproduction: pkg17 s0 disease arm (prefix rounds 0-4)
    d17 = [r for r in json.load(open(OUT / "pkg17_wide.json"))["combos"] if r["seed"] == 0][0]
    pre = [x for x in d17["rounds"] if x["g"] <= 4]
    scan = scan_trajectory(pre, ref)
    check("pkg17-s0 probe_ref fires at G0", scan["fires"].get("probe_ref") == 0)
    check("pkg17-s0 jcorr fires at G1", scan["fires"].get("jcorr") == 1)
    # 2. pkg4 comp80-s1500 probe fires G2
    d4 = [r for r in json.load(open(OUT / "pkg4_comp.json"))["combos"]
          if r["combo"].startswith("comp80xseed1500")][0]
    scan4 = scan_trajectory(d4["rounds"], ref)
    check("pkg4-comp80-s1500 probe fires by G2",
          min([v for k, v in scan4["fires"].items() if k.startswith("probe")] or [99]) <= 2)
    # 3. bottleneck correlation over tier record
    import flywheel_bottleneck as bn  # noqa: F401 (validates import surface too)
    v = json.load(open(OUT / "bottleneck_validation.json"))
    check("bottleneck r>0.6 on record", (v["pearson"] or 0) > 0.6)
    # 4. routing decisions
    check("triple-prefix routes joint",
          set(recommend(scan["fires"])) >= {"gate-judge", "quota-pool+selection"})
    check("compounding-only routes length-reg",
          recommend(scan4["fires"]) == ["length-regularize"] or
          "length-regularize" in recommend(scan4["fires"]))
    # 6. multi-pid wrongmode still fires on deep lock-in (specificity kept)
    d7 = [r for r in json.load(open(OUT / "pkg7_lockin.json"))["combos"]
          if r["arm"] == "A" and r["seed"] == 1500][0]
    scan7 = scan_trajectory(d7["rounds"], ref)
    check("wrongmode fires on deep lock-in (pkg7-A s1500)",
          "wrongmode" in scan7["fires"])
    d11 = [r for r in json.load(open(OUT / "pkg11_recover.json"))["combos"]
           if r["arm"] == "B" and r["seed"] == 0][0]
    check("archive alert fires on pkg11-A",
          len(archive_zero_alert([r for r in json.load(open(OUT / "pkg11_recover.json"))["combos"]
                                  if r["arm"] == "A" and r["seed"] == 0][0]["rounds"])) > 0)
    check("pool alert fires on pkg11-B (archive has it, pool drops it)",
          len(pool_zero_alert(d11["rounds"], "recency")) > 0)
    n_fail = sum(1 for _, c in checks if not c)
    print(f"\nkit validation: {len(checks)-n_fail}/{len(checks)} PASS")
    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

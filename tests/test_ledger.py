"""Ledger unit tests — fast, deterministic, no repo data needed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import capability_ledger as cl


def _mk_round(g, tier_corr=None, probe=None, kept_spec=(), ver=None):
    """kept_spec: list of (aid, tier, correct, misc)."""
    arts, kid = [], []
    for aid, tier, correct, misc in kept_spec:
        a = {"id": aid, "tier": tier, "problem_id": f"D{tier}-00",
             "correct": correct, "_misc": misc, "final_score": 90.0 if correct else 10.0}
        arts.append(a)
        kid.append(aid)
    # add filler train arts so train-recompute has mass
    m = {"tier_corr": tier_corr or {}, "tier_acc": [0.55, 0.55, 0.55]}
    if probe is not None:
        m["probe_tier_corr"] = probe
        m["probe_corr"] = round(sum(probe.values()) / len(probe), 3)
    return {"g": g, "metrics": m, "artifacts": arts, "kept_ids": sorted(kid),
            "model": {"version": ver or f"T-G{g}"}}


def test_wilson_basic():
    lo, hi = cl.wilson_interval(8, 10)
    assert 0.4 < lo < 0.6 and 0.9 < hi <= 1.0
    assert cl.wilson_interval(0, 0) == [0.0, 1.0]
    assert cl.wilson_interval(5, 10)[0] < 0.5 < cl.wilson_interval(5, 10)[1]


def test_frontier_flip_requires_significance():
    # tiny noisy win inside overlap -> no flip, contested
    C = [
        {"gen": "G0", "g": 0, "slice": "tier=2", "est": 0.60, "n": 16,
         "ci": cl._ci_from_acc(0.60, 16), "epistemic_class": "V"},
        {"gen": "G1", "g": 1, "slice": "tier=2", "est": 0.65, "n": 16,
         "ci": cl._ci_from_acc(0.65, 16), "epistemic_class": "V"},
    ]
    f = cl.build_frontier(C)
    assert f[0]["holder"] == "G0" and f[0]["contested"] is True
    # decisive win -> flip
    C2 = [
        {"gen": "G0", "g": 0, "slice": "tier=2", "est": 0.90, "n": 50,
         "ci": cl._ci_from_acc(0.90, 50), "epistemic_class": "V"},
        {"gen": "G1", "g": 1, "slice": "tier=2", "est": 0.40, "n": 50,
         "ci": cl._ci_from_acc(0.40, 50), "epistemic_class": "V"},
    ]
    f2 = cl.build_frontier(C2)
    assert f2[0]["holder"] == "G0" and f2[0]["regret_of_current"] == 0.5


def test_nds_and_dormant():
    r0 = _mk_round(0, probe={"0": 0.9, "1": 0.9, "2": 0.9},
                   kept_spec=[("k0", 2, True, False), ("k1", 2, True, False)])
    r1 = _mk_round(1, probe={"0": 0.92, "1": 0.91, "2": 0.55},
                   kept_spec=[("k2", 2, False, False)])
    # force decisive CIs by patching n through direct C build is probe-based;
    # here just check structure + M counts, not gating outcome
    C = cl.build_C([r0, r1])
    M = cl.build_M([r0, r1])
    assert len([e for e in C if e["instrument"] == "probe"]) == 6
    m0 = [e for e in M if e["g"] == 0 and e["slice"] == "tier=2"][0]
    assert m0["importable_mass"] == 2 and m0["quarantined"] == 0
    doc = cl.build_ledger([r0, r1], run_id="t")
    assert doc["schema"] == cl.SCHEMA
    assert 0.0 <= doc["nds"]["nds"] <= 1.0
    assert "understatement" in doc


def test_quarantine_subtracted_from_mass():
    r = _mk_round(0, probe={"0": 0.5, "1": 0.5, "2": 0.5},
                  kept_spec=[("q0", 2, True, True), ("q1", 2, True, False)])
    M = cl.build_M([r])
    m = [e for e in M if e["slice"] == "tier=2"][0]
    assert m["importable_mass"] == 1 and m["quarantined"] == 1


def test_deficit_and_pair_coverage():
    assert cl.deficit_weights([0.9, 0.5, 0.5]) == [0.091, 0.455, 0.455]
    cur = {"tier=0": 0.9, "tier=1": 0.5}
    oth = {"tier=0": 0.5, "tier=1": 0.9}
    best = {"tier=0": 0.9, "tier=1": 0.9}
    assert cl.pair_coverage(cur, oth, best) == 1.0
    assert cl.pair_coverage(cur, cur, best) < 1.0


def test_legacy_overall_slice():
    r = {"g": 0, "metrics": {"correct_rate": 0.7}, "artifacts": [],
         "kept_ids": [], "model": {"version": "L-G0"}}
    doc = cl.build_ledger([r, dict(r, g=1, model={"version": "L-G1"})])
    assert doc["slice_space"]["n"] >= 1


def test_contested_does_not_count_as_trailing():
    # flat noisy line: current point slightly above holder inside overlap
    # -> status contested, NDS 0 (avoids NDS=1 on noise)
    C = [
        {"gen": "G0", "g": 0, "slice": "tier=0", "est": 0.70, "n": 16,
         "ci": cl._ci_from_acc(0.70, 16), "epistemic_class": "V"},
        {"gen": "G1", "g": 1, "slice": "tier=0", "est": 0.75, "n": 16,
         "ci": cl._ci_from_acc(0.75, 16), "epistemic_class": "V"},
    ]
    f = cl.build_frontier(C)
    assert f[0]["status"] == "contested"
    assert cl.compute_nds(f)["nds"] == 0.0
    # decisive collapse -> trailing, NDS 1
    C2 = [
        {"gen": "G0", "g": 0, "slice": "tier=2", "est": 0.92, "n": 16,
         "ci": cl._ci_from_acc(0.92, 16), "epistemic_class": "V"},
        {"gen": "G1", "g": 1, "slice": "tier=2", "est": 0.30, "n": 16,
         "ci": cl._ci_from_acc(0.30, 16), "epistemic_class": "V"},
    ]
    f2 = cl.build_frontier(C2)
    assert f2[0]["status"] == "trailing"
    assert cl.compute_nds(f2)["nds"] == 1.0

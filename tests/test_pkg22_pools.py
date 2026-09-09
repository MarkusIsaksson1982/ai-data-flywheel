"""Pool-semantics lock (pkg22): B=unscreened quota, C=screened quota + golden backfill."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import flywheel_pkg22 as p22


def _mk(i, tier, rule, correct, misc=False):
    return {"id": f"k{i}", "tier": tier, "rule_score": rule, "final_score": rule,
            "correct": correct, "_misc": misc, "round": 0}


def test_pool_semantics():
    hist = [[_mk(i, 0, 100, True) for i in range(6)] +
            [_mk(10 + i, 1, 100, True) for i in range(6)] +
            [_mk(20 + i, 2, 30, False) for i in range(6)] +
            [_mk(30, 2, 15, False, misc=True)]]
    gold = [{**_mk(100 + i, 0, 95, True), "id": f"g{i}"} for i in range(5)]
    pa = p22.pool_for("A", hist, gold)
    pb = p22.pool_for("B", hist, gold)
    pc = p22.pool_for("C", hist, gold)
    # A: plain top-36 -> 12 correct + 6 wrong-hard + misc (poison flows)
    # A: plain top-36 -> all 19 (12 correct + 6 wrong-hard + misc): poison flows
    assert len(pa) == 19 and any(a.get("_misc") for a in pa)
    # B: unscreened quota 12/tier from 6/6/7 available
    assert [sum(1 for a in pb if a["tier"] == t) for t in (0, 1, 2)] == [6, 6, 7]
    assert any(a.get("_misc") for a in pb), "B must admit poison (unscreened)"
    # C: screened quota -> 6+6+0, golden backfill (5 golden, pool short of 36)
    assert not any(a.get("_misc") for a in pc), "C must exclude misc"
    assert all(a["rule_score"] >= 85 or a["id"].startswith("g") for a in pc), "C screened"
    assert any(a["id"].startswith("g") for a in pc), "C backfills golden when short"
    print("pool semantics OK: A=top36, B=quota+poison, C=screened+golden")

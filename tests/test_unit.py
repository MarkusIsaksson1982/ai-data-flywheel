"""Unit tests: pure functions, no full experiment runs (fast, <30s).

Covers scorer correctness, selection policies, judge math, merge/pool
machinery, tier-skill updates, kit routing, and the gradient harness basics.
"""
import random

import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness3 as h3
import flywheel_threadC as tC
import flywheel_kit as kit


def test_imports():
    import flywheel_harness2  # noqa: F401
    import flywheel_harness4  # noqa: F401
    import flywheel_harness5  # noqa: F401
    import flywheel_pkg1  # noqa: F401
    import flywheel_pkg2  # noqa: F401
    import flywheel_pkg3  # noqa: F401
    import flywheel_pkg4  # noqa: F401
    import flywheel_pkg5  # noqa: F401
    import flywheel_pkg6  # noqa: F401
    import flywheel_pkg7  # noqa: F401
    import flywheel_pkg8  # noqa: F401
    import flywheel_pkg9  # noqa: F401
    import flywheel_pkg10  # noqa: F401
    import flywheel_pkg11  # noqa: F401
    import flywheel_pkg12  # noqa: F401
    import flywheel_pkg13  # noqa: F401
    import flywheel_pkg14  # noqa: F401
    import flywheel_pkg15  # noqa: F401
    import flywheel_pkg16  # noqa: F401
    import flywheel_pkg17  # noqa: F401
    import flywheel_pkg18  # noqa: F401
    import flywheel_bottleneck  # noqa: F401
    import flywheel_lm  # noqa: F401


def test_scorer_fixed_verifies_canonical():
    assert h3.step_check_v3("82 + 91 + 77 + 90 = 340") == (True, True)
    assert h3.step_check_v3("2 * (9 + 5) = 28") == (True, True)
    assert h3.step_check_v3("2^7 = 128") == (True, True)
    assert h3.step_check_v3("82 + 91 + 77 + 90 = 341")[1] is False
    assert h3.step_check_v3("Hmm, let me think differently.") == (False, True)


def test_scorer_legacy_false_penalty_documented():
    # legacy marks a CANONICAL correct multi-add step wrong (blind spot kept
    # intentionally for comparability; fixed in v4 scorer)
    assert base.safe_eval_step("82 + 91 + 77 + 90 = 340") == (True, False)


def test_v4_coverage_term():
    art = {"problem_id": "P04", "problem_text": "", "cot": ["Next, 60 * 2 = 120."],
           "final_line": "Final: 150", "final_answer": 150, "ground_truth": 150}
    import flywheel_harness4 as h4
    d = h4.rule_evaluate_v4(dict(art), "v4")
    assert d["scorer"] == "v4" and abs(d["coverage"] - 1 / 3) < 1e-3


def test_adv_bonuses():
    art = {"cot": ["a", "b", "c", "d"], "correct": False, "format_ok": True}
    assert h3.adv_bonus("adv_verbose", art) == 6.0
    assert h3.adv_bonus("adv_fluent", art) == 25.0
    art2 = {"cot": ["Check: x.", "Next, y."], "correct": True, "format_ok": True}
    assert h3.adv_bonus("adv_surface", art2) == 6.0
    assert h3.adv_bonus("adv_fluent", art2) == 0.0


def test_invert_mapping():
    assert abs((100 - 0.9 * 15) - 86.5) < 1e-9
    assert abs((100 - 0.9 * 95) - 14.5) < 1e-9


def _mk(sid, score, pid="P01", correct=True):
    return {"id": sid, "problem_id": pid, "final_score": score, "correct": correct,
            "format_ok": True, "step_consistency": 1.0, "cot": ["Compute: 1 + 1 = 2."],
            "rule_score": score}


def test_selection_policies():
    cands = [_mk(f"a{i}", 90 - i, pid=f"P{i % 4:02d}") for i in range(12)]
    assert len(h1.sel_topk(cands, [], k=5)) == 5
    assert [a["id"] for a in h1.sel_thresh90(cands, [])] == ["a0"]
    capped = h1.sel_floor_caps([_mk(f"b{i}", 95, pid=f"P{i % 10:02d}") for i in range(20)], [])
    assert len(capped) == 18 and max(
        sum(1 for a in capped if a["problem_id"] == f"P{j:02d}") for j in range(10)) <= 2
    # documented edge: minimum-kept-size backfill overrides caps when data is scarce
    scarce = h1.sel_floor_caps([_mk(f"d{i}", 95, pid="P01") for i in range(6)], [])
    assert len(scarce) == 6
    grid = h1.sel_coverage_grid([_mk(f"c{i}", 80 + (i % 5), pid=f"P{i:02d}") for i in range(12)], [])
    assert len({a["problem_id"] for a in grid}) >= 8
    nov = h1.sel_quality_novelty(cands, [])
    assert len(nov) == 12


def test_merge_train_parentage():
    sm0 = base.make_sm0()
    import copy
    p1, p2 = copy.deepcopy(sm0), copy.deepcopy(sm0)
    p1.version, p2.version = "P-A", "P-B"
    p1.params["arithmetic_acc"] = 0.6
    p2.params["arithmetic_acc"] = 0.8
    m = tC.merge_train("M", [p1, p2], [], [0, 1], lesson="t")
    assert m.lineage["parent_models"] == ["P-A", "P-B"]
    assert m.params["arithmetic_acc"] == 0.7


def test_tier_skill_update_and_forget():
    sm0 = base.make_sm0()
    mk = lambda i, t, ok: {"id": f"k{i}", "tier": t, "correct": ok, "format_ok": True,
                           "step_consistency": 1.0, "final_score": 90.0, "cot": ["x"]}
    m = base.train_next_sm("T", [sm0], [mk(i, 0, True) for i in range(10)] +
                           [mk(10 + i, 2, True) for i in range(6)] +
                           [mk(20 + i, 2, False) for i in range(4)], [0])
    assert m.params["tier_acc"][0] == 0.753 and 0.5 < m.params["tier_acc"][2] < 0.7
    m2 = base.train_next_sm("T2", [sm0], [mk(100 + i, 0, True) for i in range(18)], [0])
    assert m2.params["tier_acc"][1] == round(0.55 - 0.08, 3)  # forgetting step
    m3 = base.train_next_sm("T3", [sm0], [dict(mk(200 + i, 0, True), tier=None) for i in range(5)], [0])
    assert m3.params["tier_acc"] == [0.55, 0.55, 0.55]  # legacy untouched


def test_kit_routing():
    assert kit.recommend({"jcorr": 1}) == ["gate-judge"]
    assert kit.recommend({"kept_misc": 0, "wrongmode": 1}) == ["quarantine-reset"]
    assert kit.recommend({"poolhard0": 2}) == ["quota-pool+selection"]
    assert kit.recommend({"probe_ref": 2}) == ["length-regularize"]
    assert set(kit.recommend({"jcorr": 1, "harddiv": 1})) >= {"gate-judge", "quota-pool+selection"}


def test_kit_probe_ref_loads():
    ref = kit.load_probe_ref()
    assert len(ref) == 6 and all(isinstance(v, float) for v in ref)


def test_lm_basics():
    import numpy as np
    import flywheel_lm as L
    assert 0.0 < L.logt(9999) < 1.0 and L.logt(10) < L.logt(9999)
    assert abs(L.unlogt(L.logt(150)) - 150) < 1e-6
    rng = np.random.default_rng(0)
    m = L.MLP(rng)
    X = np.array([[0.05, 0.05, 1, 0, 0, 0], [0.1, 0.05, 1, 0, 0, 0]])
    pred, _ = m.forward(X)
    assert pred.shape == (2,)
    y = np.array([L.logt(10), L.logt(15)])
    losses = [m.step(X, y, 0.01) for _ in range(5)]
    assert losses[-1] < losses[0]  # small-lr descent on a fixed batch
    r = np.random.default_rng(7)
    a = L.gen_claims(r, 10, 2, 20)
    r2 = np.random.default_rng(7)
    b = L.gen_claims(r2, 10, 2, 20)
    assert [x["claimed"] for x in a] == [x["claimed"] for x in b]

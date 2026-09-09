"""BH-gated frontier tests (FDR hardening ported from Nemotron session).

Default path (fdr=None) must remain bit-identical to Wilson-only behavior.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import capability_ledger as cl


def test_bh_basic():
    assert cl.benjamini_hochberg([], 0.05) == []
    # strong signal survives, weak one filtered at family level
    assert cl.benjamini_hochberg([0.001, 0.04, 0.5], 0.05) == [True, False, False]
    assert cl.benjamini_hochberg([0.5, 0.6], 0.05) == [False, False]


def test_flip_pvalue_sane():
    assert cl._flip_pvalue(0.9, 50, 0.5, 50) < 0.01
    assert cl._flip_pvalue(0.55, 16, 0.5, 16) > 0.2  # noisy near-tie, not significant
    assert cl._flip_pvalue(0.5, 0, 0.5, 0) == 1.0  # degenerate -> never significant


def _C(rows):
    return [{"gen": f"G{g}", "g": g, "slice": "tier=2", "est": e,
             "n": 16, "ci": cl._ci_from_acc(e, 16)} for g, e in rows]


def test_default_path_unchanged():
    C = _C([(0, 0.5), (1, 0.9)])
    assert cl.build_frontier(C) == cl.build_frontier(C, fdr=None)


def test_fdr_keeps_decisive_flips():
    C = _C([(0, 0.2), (1, 0.9)])
    assert cl.build_frontier(C, fdr=0.05)[0]["holder"] == "G1"


def test_fdr_matches_plain_on_realistic_families():
    # Wilson pre-gating admits only flips with normal-p << BH thresholds, so on
    # realistic families the FDR path must equal the plain path (conservative by
    # construction; verified here, not assumed). BH bites only in the narrow
    # Wilson/normal-approximation disagreement band (covered by unit tests).
    C = [{"gen": f"G{g}", "g": g, "slice": f"tier={s}", "est": e,
            "n": 16, "ci": cl._ci_from_acc(e, 16)}
           for s in range(6) for g, e in ((0, 0.45), (1, 0.55), (2, 0.90))]
    assert cl.build_frontier(C, fdr=0.05) == cl.build_frontier(C)

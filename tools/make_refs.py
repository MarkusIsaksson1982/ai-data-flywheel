"""Regenerate tracked reference files from the current deterministic codebase.

- refs/probe_ref.json : pooled healthy-control probe trajectory (pkg4 controls).
  Consumed by flywheel_kit.load_probe_ref() and by pkg6/pkg17 instead of the
  multi-MB pkg4_comp.json, so fresh clones work without generated data.
- tests/expected.json : fingerprint of fast deterministic computations used by
  tests/test_repro.py to verify bit-identical reproduction.

Usage: python tools/make_refs.py   (reads ../harness4 outputs if present for
probe_ref; otherwise probe_ref must already exist — it is tracked in git)
"""
from __future__ import annotations
import json
import random
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import flywheel_sim as base
import flywheel_harness3 as h3
import flywheel_pkg9 as p9

OUT_REFS = ROOT / "refs"
OUT_TESTS = ROOT / "tests"


def make_probe_ref():
    d = json.load(open(ROOT / "pkg4_comp.json"))["combos"]
    ctrls = [r for r in d if r["arm"] == "control"]
    ref = [round(mean(r["rounds"][g]["metrics"]["probe_corr"] for r in ctrls), 3)
           for g in range(len(ctrls[0]["rounds"]))]
    return ref


def fingerprint():
    """Small, fast, fully deterministic computations covering the stack."""
    fp = {}
    # 1. procedural bank head (domain + scorer substrate)
    bank = p9.make_bank(777, 16, "D")
    fp["bank_head"] = bank[0]
    probe_bank = p9.make_bank(31337, 8, "Q")
    fp["probe_head"] = probe_bank[0]
    # 2. scorer on fixed artifacts (legacy / fixed / v4 incl. coverage)
    art = {"problem_id": "P07", "problem_text": "", "cot": ["Next, 82 + 91 + 77 + 90 = 340."],
           "final_line": "Final: 85", "final_answer": 85, "ground_truth": 85}
    fp["legacy_P07"] = base.rule_evaluate(art)
    fp["fixed_P07"] = h3.rule_evaluate_v3(dict(art), "fixed")
    # 3. golden set scores (judge calibration substrate)
    import flywheel_harness as h1
    gold = h1.make_golden_set()
    fp["golden_rule"] = [a["rule_score"] for a in gold]
    jrng = random.Random(777)
    sm0 = base.make_sm0()
    raw = [h1._blind_raw(a["rule_score"], sm0, jrng) for a in gold]
    fp["golden_calib"] = list(h1._fit_affine(raw, [a["rule_score"] for a in gold]))
    # 4. mini flywheel: 2 rounds, SM-0 -> train -> generate (end-to-end)
    sm = base.make_sm0()
    a0 = base.generate_batch(sm, 0, 3, 20260907)
    base.evaluate_batch(a0, None, 1.0, 11)
    kept = base.select_kept(a0, thresh=70.0)
    sm1 = base.train_next_sm("SM-1", [sm], kept, [0], temp_override=0.85, lesson="fp")
    a1 = base.generate_batch(sm1, 1, 3, 20260907 + 100)
    base.evaluate_batch(a1, None, 1.0, 18)
    fp["mini"] = {"r0": base.round_metrics(a0), "r1": base.round_metrics(a1),
                  "kept0": len(kept), "sm1_params": sm1.params}
    return fp


def main():
    OUT_REFS.mkdir(exist_ok=True)
    OUT_TESTS.mkdir(exist_ok=True)
    try:
        ref = make_probe_ref()
        with open(OUT_REFS / "probe_ref.json", "w") as f:
            json.dump({"ref": ref, "source": "pkg4_comp.json healthy controls pooled",
                       "note": "tracked; regenerating requires the full pkg4 run"}, f, indent=1)
        print("wrote refs/probe_ref.json:", ref)
    except FileNotFoundError as e:
        print("probe_ref source missing (expected on fresh clones):", e)
    fp = fingerprint()
    with open(OUT_TESTS / "expected.json", "w") as f:
        json.dump(fp, f, indent=1, sort_keys=True, default=str)
    print("wrote tests/expected.json")


if __name__ == "__main__":
    main()

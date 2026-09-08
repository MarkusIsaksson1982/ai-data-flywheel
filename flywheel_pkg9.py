"""
Package 9 — Procedural problem bank + difficulty-tier forgetting (frozen platform)
==================================================================================
FROZEN DOCTRINE (one paragraph, locked): incident response = multi-channel
tripwires (probe-reference + drop, kept_misc/wrongmode, drift-vs-G0, gating)
with first-fire-wins and 0-FP record; channel priority is failure-class
dependent (probe leads compounding, misc-channels lead lock-in). Responses are
diagnosis-matched: compounding -> forward length regularization (partial,
~+0.2, never rollback); lock-in -> judge repair only if correct-mass >=
kept-size else quarantined generation reset (fresh params + golden/screened
data + screened continuation, 3-5 rounds to rebuild). Defaults: v4 scorer,
blind gated097, recency-36, single parent (merge only above compl 0.5),
length-bin cap hygiene, probe+provenance tripwires. Evidence: pkg1-8 + harnesses.

NEW THREAD (A: procedural bank): the 12-problem hand bank is exhausted —
signatures saturate by G5 (dup_high->1.0 even in healthy controls), probes are
hand-made, and single difficulty hides curriculum effects. Procedural bank:
48 problems (16/tier; tiers = 1/2/3-4 canonical steps), fixed bank-seed for
comparability + a FRESH-SEED held-out probe bank (24 problems; genuinely OOD,
unlike hand variants). Tests: (1) does signature saturation lift with bank
size? (2) does top-k selection starve hard tiers (curriculum collapse — a NEW
mode the fixed bank cannot show)? (3) does tier-stratified selection (top-6
per tier) preserve hard capability vs plain top-18?
Arms (matched budgets, NPP=3 -> 144 arts/round, kept 18, 6 rounds, seeds x3):
  plain   : top-18 by final_score (frozen default)
  strat   : top-6 per tier by final_score (quota intervention)
Training recency-36 by final, temp fixed .85, blind gated097 scores, misc 0.

Usage: python flywheel_pkg9.py (6 combos)
Out: pkg9_bank.json
"""
from __future__ import annotations
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness4 as h4
import flywheel_pkg2 as p2

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
BANK_SEED = 777
PROBE_BANK_SEED = 31337
N_PER_TIER = 16

SURFACES = [
    "A farmer has {a} apples and buys {b} more. How many in total?",
    "Compute {a} + {b}.",
    "A box contains {a} packs of {b} stickers. How many stickers?",
    "A train covers {a} km, then {b} km more. Total distance?",
]


def _chain(rng, n_ops, lo, hi):
    """Build a true n-op chain; returns (text, answer, steps). Addition/multiplication
    heavy with guarded subtraction (non-negative intermediates)."""
    a = rng.randint(lo, hi)
    b = rng.randint(lo, hi)
    if n_ops == 1:
        op = rng.choice(["+", "+", "*"])
        ans = a + b if op == "+" else a * b
        return f"Compute {a} {op} {b}.", ans, [f"{a} {op} {b} = {ans}"]
    # multi-op: left-associative chain with running total (always valid equations)
    total, steps = a, []
    parts = [str(a)]
    for _ in range(n_ops):
        op = rng.choice(["+", "+", "*", "-"])
        c = rng.randint(2, hi // 2 + 2)
        if op == "-" and total - c < 0:
            op = "+"
        new = total + c if op == "+" else (total * c if op == "*" else total - c)
        steps.append(f"{total} {op} {c} = {new}")
        parts.append(f"{op} {c}")
        total = new
    return f"Compute {' '.join(parts)}.", total, steps


def make_bank(bank_seed, n_per_tier, tag):
    rng = random.Random(bank_seed)
    bank = []
    cfgs = [(1, 2, 20), (2, 2, 50), (3, 2, 99)]
    for tier, (n_ops, lo, hi) in enumerate(cfgs):
        for i in range(n_per_tier):
            if tier == 2 and rng.random() < 0.4:
                n_ops = 4
            text, ans, steps = _chain(rng, n_ops, lo, hi)
            if tier == 0 and rng.random() < 0.5:
                text = rng.choice(SURFACES).format(a=steps[0].split()[0], b=steps[0].split()[2])
            bank.append({"pid": f"{tag}{tier}-{i:02d}", "tier": tier, "text": text,
                         "answer": ans, "steps": steps})
    # verify every canonical step (fixed scorer must confirm all correct)
    for p in bank:
        for s in p["steps"]:
            chk, ok = h3_step(s)
            assert chk and ok, (p["pid"], s)
    return bank


def h3_step(s):
    import flywheel_harness3 as h3
    return h3.step_check_v3(s)


BANK = make_bank(BANK_SEED, N_PER_TIER, "D")
PROBE_BANK = make_bank(PROBE_BANK_SEED, 8, "Q")
base.PROBLEM_BY_ID.update({p["pid"]: p for p in BANK + PROBE_BANK})  # additive only


def gen_batch(sm, bank, rnd, npp, seed, aid_prefix):
    rng = random.Random(seed)
    probs = list(bank) * npp
    rng.shuffle(probs)
    arts = []
    for k, prob in enumerate(probs, 1):
        a = base.generate_artifact(sm, prob, f"{aid_prefix}{k:03d}", rnd, rng)
        a["tier"] = prob["tier"]
        arts.append(a)
    return arts


def select_current(arts, arm):
    if arm == "plain":
        return sorted(arts, key=lambda a: a["final_score"], reverse=True)[:18]
    out = []
    for t in (0, 1, 2):
        tier = sorted([a for a in arts if a["tier"] == t],
                      key=lambda a: a["final_score"], reverse=True)[:6]
        out.extend(tier)
    return out


def pool_for(kept_hist):
    src = [a for h in kept_hist[-3:] for a in h]
    seen, out = set(), []
    for a in sorted(src, key=lambda a: a["final_score"], reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def tier_corr(arts):
    out = {}
    for t in (0, 1, 2):
        sub = [a for a in arts if a["tier"] == t]
        out[t] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else None
    return out


def run_arm(arm, seed):
    tag = f"{arm}xseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    kept_hist: list = []
    sig_archive: set = set()
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    for g in range(6):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        sm.params["temperature"] = 0.85
        arts = gen_batch(sm, BANK, g, NPP, gs, f"R{g}-{arm}-")
        if g == 0:
            for a in arts:
                a.update(h4.rule_evaluate_v4(a, "v4"))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only",
                          "judge_kind": None, "alpha_rule": None})
        else:
            alpha = 0.8 if (prev_corr is not None and
                            (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            h4.evaluate_v4(arts, sm, "blind", alpha, js, (1.0, 0.0), "v4")
        kept = select_current(arts, arm)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "normal", tag
        sigs = [p2.path_sig(a) for a in kept]
        new_path = round(sum(1 for s in sigs if s not in sig_archive) / max(1, len(sigs)), 3)
        dup_high = round(sum(1 for s, a in zip(sigs, kept)
                             if a["rule_score"] >= 85 and s in sig_archive) / max(1, len(kept)), 3)
        for s in sigs:
            sig_archive.add(s)
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["kept_tier_share"] = {str(t): sum(1 for a in kept if a["tier"] == t) for t in (0, 1, 2)}
        m["new_path_rate"] = new_path
        m["dup_high_rate"] = dup_high
        probe = gen_batch(sm, PROBE_BANK, g, 2, BASE_SEED + seed + 9000 + g * 100, f"PRB{g}-")
        for a in probe:
            a.update(h4.rule_evaluate_v4(a, "v4"))
            a["final_score"] = a["rule_score"]
        probe_corr = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_corr"] = probe_corr
        pool = pool_for(kept_hist + [kept]) if kept_hist else list(kept)
        nxt = None
        if g < 5:
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[normal|{arm}]")
        rounds_out.append({"g": g, "arm": arm, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "probe_corr": probe_corr,
                           "probe_sample": [{"id": a["id"], "correct": a["correct"]} for a in probe],
                           "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        print(f"{tag} G{g}: corr={m['correct_rate']} tiers={m['tier_corr']} "
              f"keptshare={m['kept_tier_share']} probe={probe_corr} newpath={new_path}", flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "rounds": rounds_out}


def main():
    combos = [(a, o) for a in ["plain", "strat"] for o in SEEDS]
    print(f"--- pkg9 bank: {len(combos)} combos (144 arts/round) ---")
    results = [run_arm(*c) for c in combos]
    with open(OUT / "pkg9_bank.json", "w") as f:
        json.dump({"block": "bank", "bank_seed": BANK_SEED,
                   "probe_bank_seed": PROBE_BANK_SEED, "combos": results}, f, indent=1)
    print("Wrote pkg9_bank.json")


if __name__ == "__main__":
    main()

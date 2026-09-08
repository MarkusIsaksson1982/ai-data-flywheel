"""
Package 2 — Goodhart / provenance / capability ceiling (frozen platform)
=========================================================================
Frozen libs imported, not modified. OOD probe + provenance + proxy pressure.

PROBE SET (12 held-out variants, rule-verifiable, never trained on):
  Q01-Q06 surface variants (new numbers/names, same reasoning); Q07-Q12
  structural variants (+1 reasoning step or harder checks). Generated with the
  SAME generator (NPP=2, 24 probe arts/round) and scored with the v4 scorer.

PROVENANCE: path signature = tuple of whitespace-stripped 'a op b = c'
  equations in order of appearance across the CoT (('prose',) if none).
  near-dup = signature seen in any earlier KEPT artifact. Metrics: new_path_rate
  (kept with unseen sig), dup_high (kept with rule>=85 and seen sig),
  mean kept CoT length.

PROXY PRESSURE: selection/training rank by proxy = rule_score + 12*len(cot)
  (uncapped verbosity reward — deliberately Goodhart-able).
  Arms (matched 36-pools; pools ranked by the arm's own selection score):
    control  : rank by final_score (frozen default).
    goodhart : rank by proxy.
    guarded  : rank by proxy + 15*novelty, greedy top-18 with cap 8 per
               length-bin (novelty bonus + diversity floor in one mechanism).
Questions: does the proxy rise while probe stagnates/drops (Q1)? Is improvement
rediscovery (dup_high up, new_path down — Q2)? Does the guardrail hold (Q3)?

Protocol: 6 normal rounds (G0-G5), seeds 0/1500/3000. 9 combos.
Out: pkg2_goodhart.json
"""
from __future__ import annotations
import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness3 as h3
import flywheel_harness4 as h4

OUT = Path(__file__).parent
NPP = 3
# Additive registration only: base sim iterates PROBLEMS (unchanged); this just
# lets the v4 scorer's PROBLEM_BY_ID lookup resolve probe pids for coverage.

PROBE_NPP = 2
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
LENBIN_CAP = 8

PROBE = [
    {"pid": "Q01", "text": "Liam has 23 marbles, buys 11 more, then gives away 9. How many left?", "answer": 25,
     "steps": ["23 + 11 = 34", "34 - 9 = 25"]},
    {"pid": "Q02", "text": "A tray holds 7 rows of 9 buns. If 17 are eaten, how many remain?", "answer": 46,
     "steps": ["7 * 9 = 63", "63 - 17 = 46"]},
    {"pid": "Q03", "text": "Solve: 4x + 5 = 37. What is x?", "answer": 8,
     "steps": ["4x = 37 - 5 = 32", "x = 32 / 4 = 8"]},
    {"pid": "Q04", "text": "A car travels 70 km/h for 3.5 hours. How far (km)?", "answer": 245,
     "steps": ["70 * 3 = 210", "70 * 0.5 = 35", "210 + 35 = 245"]},
    {"pid": "Q05", "text": "Street lamps flash every 5th and every 7th minute. First joint flash after minute 0?", "answer": 35,
     "steps": ["multiples of 5: 5, 10, 15, 20, 25, 30, 35", "multiples of 7: 7, 14, 21, 28, 35", "first common = 35"]},
    {"pid": "Q06", "text": "Rectangle 11 by 4. Perimeter?", "answer": 30,
     "steps": ["2 * (11 + 4) = 30"]},
    {"pid": "Q07", "text": "Noah scored 88, 92, 76, 84, 90. Average?", "answer": 86,
     "steps": ["88 + 92 + 76 + 84 + 90 = 430", "430 / 5 = 86"]},
    {"pid": "Q08", "text": "If 3 workers build 6 sheds in 4 days, how many sheds can 6 workers build in 8 days?", "answer": 24,
     "steps": ["6 / (3 * 4) = 0.5 sheds per worker-day", "6 * 8 * 0.5 = 24"]},
    {"pid": "Q09", "text": "Next prime after 50?", "answer": 53,
     "steps": ["50, 51, 52 composite", "53 has no divisors except 1,53"]},
    {"pid": "Q10", "text": "3^4 minus 50?", "answer": 31,
     "steps": ["3^4 = 81", "81 - 50 = 31"]},
    {"pid": "Q11", "text": "A shop gives 25% off $120, then a further $10 off. Final price?", "answer": 80,
     "steps": ["25% of 120 = 30", "120 - 30 = 90", "90 - 10 = 80"]},
    {"pid": "Q12", "text": "Sum of integers 1..30?", "answer": 465,
     "steps": ["n(n+1)/2 = 30*31/2", "30*31=930, /2=465"]},
]
base.PROBLEM_BY_ID.update({p["pid"]: p for p in PROBE})


def path_sig(art):
    parts = []
    for s in art["cot"]:
        for mm in base.ARITH_RE.finditer(s):
            parts.append(re.sub(r"\s+", "", mm.group(0)))
    return tuple(parts) if parts else ("prose",)


def proxy_of(art):
    return art["rule_score"] + 12 * len(art["cot"])


def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def select_current(arts, kept_hist, arm):
    if arm == "control":
        return h1.sel_topk(arts, kept_hist, k=18)
    if arm == "goodhart":
        return sorted(arts, key=proxy_of, reverse=True)[:18]
    if arm == "guarded":
        freq = Counter(_bucket(a) for h in kept_hist for a in h)
        def score(a):
            return proxy_of(a) + 15 * (1.0 / (1.0 + freq[_bucket(a)]))
        ranked = sorted(arts, key=score, reverse=True)
        kept, perbin = [], Counter()
        for a in ranked:  # diversity floor via per-length-bin cap
            b = min(len(a["cot"]), 5)
            if perbin[b] < LENBIN_CAP:
                kept.append(a)
                perbin[b] += 1
                freq[_bucket(a)] += 1
            if len(kept) >= 18:
                break
        return kept
    raise ValueError(arm)


def pool_for(arm, kept_hist):
    """Recency-36 ranked by the arm's own selection score (pressure infects data)."""
    hists = ([kept_hist[-3]] if len(kept_hist) >= 3 else []) + \
            ([kept_hist[-2]] if len(kept_hist) >= 2 else []) + [kept_hist[-1]]
    src = [a for h in hists for a in h]
    if arm == "control":
        key = lambda a: a["final_score"]
    elif arm == "goodhart":
        key = proxy_of
    else:
        freq = Counter(_bucket(a) for h in kept_hist for a in h)
        key = lambda a: proxy_of(a) + 15 * (1.0 / (1.0 + freq[_bucket(a)]))
    seen, out = set(), []
    for a in sorted(src, key=key, reverse=True):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= 36:
            break
    return out


def gen_probe(sm, g, seed):
    rng = random.Random(BASE_SEED + seed + 9000 + g * 100)
    arts = []
    for i, prob in enumerate(PROBE * PROBE_NPP):
        arts.append(base.generate_artifact(sm, prob, f"PRB{g}-{i:02d}", g, rng))
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    return arts


def run_arm(arm, seed):
    tag = f"{arm}xseed{seed}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    kept_hist: list = []
    sig_archive: set = set()  # path sigs of all earlier KEPT artifacts
    rounds_out: list = []
    for g in range(6):
        gs, js = BASE_SEED + seed + g * 100, BASE_SEED + seed + g * 7 + 11
        arts = base.generate_batch(sm, g, NPP, gs)
        if g == 0:
            for a in arts:
                a.update(h4.rule_evaluate_v4(a, "v4"))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only",
                          "judge_kind": None, "alpha_rule": None})
        else:
            h4.evaluate_v4(arts, sm, "blind", 0.5, js, (1.0, 0.0), "v4")
        kept = select_current(arts, kept_hist, arm)
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "normal", tag
        # provenance (against sigs strictly before this round)
        sigs = [path_sig(a) for a in kept]
        new_path = round(sum(1 for s in sigs if s not in sig_archive) / max(1, len(sigs)), 3)
        dup_high = [a for a in kept if a["rule_score"] >= 85 and path_sig(a) in sig_archive]
        for s in sigs:
            sig_archive.add(s)
        m = h1.compute_round_metrics(arts, kept)
        probe = gen_probe(sm, g, seed)
        probe_corr = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_corr"] = probe_corr
        m["proxy_true_gap"] = round(m["correct_rate"] - probe_corr, 3)
        m["new_path_rate"] = new_path
        m["dup_high_rate"] = round(len(dup_high) / max(1, len(kept)), 3)
        m["mean_kept_len"] = round(mean(len(a["cot"]) for a in kept), 2)
        m["mean_kept_proxy"] = round(mean(proxy_of(a) for a in kept), 1)
        pool = pool_for(arm, kept_hist + [kept]) if kept_hist else list(kept)
        makeup = {str(r): sum(1 for a in pool if a["round"] == r) for r in sorted({a["round"] for a in pool})}
        nxt = None
        if g < 5:
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[normal|{arm}]")
        rounds_out.append({"g": g, "arm": arm, "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "pool_makeup": makeup,
                           "artifacts": arts,
                           "probe_sample": [{"id": a["id"], "problem_id": a["problem_id"],
                                             "correct": a["correct"],
                                             "rule_score": a["rule_score"]} for a in probe]})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        print(f"{tag} G{g}: main={m['correct_rate']} probe={probe_corr} gap={m['proxy_true_gap']} "
              f"keptlen={m['mean_kept_len']} newpath={new_path} duphigh={m['dup_high_rate']} "
              f"proxy={m['mean_kept_proxy']}", flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "rounds": rounds_out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["goodhart", "all"], default="all")
    args = ap.parse_args()
    combos = [(a, o) for a in ["control", "goodhart", "guarded"] for o in SEEDS]
    print(f"--- block goodhart: {len(combos)} combos ---")
    results = [run_arm(*c) for c in combos]
    with open(OUT / "pkg2_goodhart.json", "w") as f:
        json.dump({"block": "goodhart", "combos": results}, f, indent=1)
    print("Wrote pkg2_goodhart.json")


if __name__ == "__main__":
    main()

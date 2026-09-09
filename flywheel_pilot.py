"""
Pilot — qwen2.5:1.5b in the scored-artifact loop (frozen platform + live model)
===============================================================================
Wires Ollama /api/generate output into the frozen evaluation path. No training
(SFT/LoRA out of scope — this pilot characterizes generation + selection
dynamics, margin/bias, and pool-mass logging with a real model).
Bank: 24 procedural problems (8/tier, bank seed locked) + 12-problem
fresh-seed probe bank (4/tier). 1 trace per problem per round (stdlib urllib).
Prompt: problem + brief-CoT instruction + explicit Final line. Parse: Final
regex, last-integer fallback. Temperature: model default (not set).
Arms (selection ranking only; generation identical):
  control : rank final_score (rule)
  invert  : rank invert score 100-0.9*rule + tiny noise (pure0)
  gated   : adaptive alpha (0.8 if prev corr<0.97 or |bias|>1.5 else 0.5),
            rank alpha*rule+(1-alpha)*judge (expect alpha 0.8 throughout)
Rounds G0-G2, seeds 0/1500/3000 (ollama options.seed = base+g; --seed runs one).
Kept 12/round (half of 24 — matches the 12-24 batch guidance and keeps the
selection cut meaningful). Probe 12/round. No SFT: rounds measure selection
stability + sampling variance (reported honestly as baseline characterization).

Usage: python flywheel_pilot.py --seed 0   (writes pilot_seed0.json)
"""
from __future__ import annotations
import argparse
import json
import random
import re
import time
import urllib.request
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness4 as h4
import flywheel_pkg9 as p9

OUT = Path(__file__).parent
MODEL = "qwen2.5:1.5b"
API = "http://localhost:11434/api/generate"
BANK = p9.make_bank(20260, 8, "W")
PROBE_BANK = p9.make_bank(424242, 4, "X")
base.PROBLEM_BY_ID.update({p["pid"]: p for p in BANK + PROBE_BANK})  # additive only
BASE_SEED = 20260907
NPP = 1
N_ROUNDS = 3
KEPT_N = 12


def ask(prompt, seed, timeout=150):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"seed": seed, "num_predict": 150}}).encode()
    last = None
    for _ in range(3):
        try:
            req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
            return d.get("response", ""), d.get("eval_count", 0)
        except Exception as e:  # retry, then mark failed
            last = e
            time.sleep(2)
    return "", 0


FINAL_RE = re.compile(r"Final:\s*(-?\d+)")
INT_RE = re.compile(r"-?\d+")


def to_artifact(text, problem, aid, rnd, secs, ntok):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    finals = FINAL_RE.findall(text)
    if finals:
        ans, fline = int(finals[-1]), f"Final: {finals[-1]}"
    else:
        ints = INT_RE.findall(text)
        ans, fline = (int(ints[-1]), f"answer is about {ints[-1]}??") if ints else (0, "no-number??")
    cot = [l for l in lines if l != fline] or lines[:1]
    return {"id": aid, "round": rnd, "model_version": MODEL, "problem_id": problem["pid"],
            "problem_text": problem["text"], "cot": cot[:4], "final_line": fline,
            "final_answer": ans, "ground_truth": problem["answer"], "tier": problem["tier"],
            "gen_seconds": round(secs, 2), "gen_tokens": ntok,
            "lineage": {"model": MODEL, "model_parents": [], "model_data_rounds": []}}


PROMPT_TMPL = ("Solve briefly in 1-2 steps. End with a line exactly like: Final: <number>\n"
               "Problem: {text}")


def gen_batch(bank, rnd, seed, tag):
    arts = []
    for k, prob in enumerate(bank, 1):
        t0 = time.time()
        text, ntok = ask(PROMPT_TMPL.format(text=prob["text"]), BASE_SEED + seed + rnd * 100 + k)
        arts.append(to_artifact(text, prob, f"{tag}-{k:03d}", rnd, time.time() - t0, ntok))
    return arts


def judge_of(rule, rng, sigma=5.0):
    # sigma=5: near-deterministic (pilot: gated ranking provably ≡ rule).
    # sigma=20: realistic residual noise — flips adjacent ranks often, so the
    # gated arm becomes a non-vacuous containment test.
    return round(max(0, min(100, 100 - 0.9 * rule + rng.gauss(0, sigma))), 1)


def run_round(arts, arm, kept_hist, seed, g):
    for a in arts:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    rng = random.Random(BASE_SEED + seed + g * 7 + 11)
    sigma = 20.0 if arm == "gated_noisy" else 5.0
    if arm == "control":
        for a in arts:
            a.update({"judge_version": None, "judge_score": None, "eval_mix": "rule-only"})
    else:
        for a in arts:
            a["judge_score"] = judge_of(a["rule_score"], rng, sigma)
            a["judge_version"], a["judge_kind"] = ("invert-fn", arm)
        if arm == "invert":
            for a in arts:
                a["final_score"] = a["judge_score"]
                a["eval_mix"] = "invert pure0"
            alpha = 0.0
        else:
            alpha = 0.5  # refined below from batch judge/rule agreement
            js = [a["judge_score"] for a in arts]
            rs = [a["rule_score"] for a in arts]
            mx, my = mean(js), mean(rs)
            den = (sum((x - mx) ** 2 for x in js) * sum((y - my) ** 2 for y in rs)) ** 0.5
            corr = round(sum((x - mx) * (y - my) for x, y in zip(js, rs)) / den, 3) if den else None
            bias = round(mean(j - r for j, r in zip(js, rs)), 2)
            alpha = 0.8 if (corr is not None and (corr < 0.97 or abs(bias) > 1.5)) else 0.5
            for a in arts:
                a["final_score"] = round(alpha * a["rule_score"] + (1 - alpha) * a["judge_score"], 1)
                a["eval_mix"] = f"gated alpha={alpha}"
            arts[0]["_gate"] = {"corr": corr, "bias": bias, "alpha": alpha}
    kept = sorted(arts, key=lambda a: a["final_score"], reverse=True)[:KEPT_N]
    kid = {a["id"] for a in kept}
    for a in arts:
        a["kept"] = a["id"] in kid
    return arts, kept


def tier_corr(arts):
    return {str(t): round(mean(1.0 if a["correct"] else 0.0
                               for a in arts if a["tier"] == t), 3) for t in (0, 1, 2)}


def run_arm(arm, seed):
    tag = f"{arm}xseed{seed}"
    kept_hist, rounds, fails = [], [], 0
    for g in range(N_ROUNDS):
        arts = gen_batch(BANK, g, seed, f"R{g}-{arm}")
        fails += sum(1 for a in arts if a["gen_tokens"] == 0)
        arts, kept = run_round(arts, arm, kept_hist, seed, g)
        probe = gen_batch(PROBE_BANK, g, seed, f"PRB{g}-")
        for a in probe:
            a.update(h4.rule_evaluate_v4(a, "v4"))
            a["final_score"] = a["rule_score"]
        m = h1.compute_round_metrics(arts, kept)
        m["tier_corr"] = tier_corr(arts)
        m["probe_corr"] = round(mean(1.0 if a["correct"] else 0.0 for a in probe), 3)
        m["probe_tier_corr"] = tier_corr(probe)
        m["kept_tier_share"] = {str(t): sum(1 for a in kept if a["tier"] == t) for t in (0, 1, 2)}
        m["mean_secs"] = round(mean(a["gen_seconds"] for a in arts), 2)
        m["mean_toks"] = round(mean(a["gen_tokens"] for a in arts), 1)
        # judge_corr / leniency_bias already set by compute_round_metrics
        kept_hist.append(kept)
        pool = sorted([a for h in kept_hist[-3:] for a in h],
                      key=lambda a: a["final_score"], reverse=True)[:36]
        m["pool_hard"] = sum(1 for a in pool if a["tier"] == 2)
        rounds.append({"g": g, "arm": arm, "metrics": m, "kept_ids": sorted(a["id"] for a in kept),
                       "probe_sample": [{"id": a["id"], "correct": a["correct"]} for a in probe],
                       "artifacts": arts})
        print(f"{tag} G{g}: corr={m['correct_rate']} tiers={m['tier_corr']} "
              f"probe={m['probe_corr']} keptshare={m['kept_tier_share']} "
              f"poolhard={m['pool_hard']} sec={m['mean_secs']}", flush=True)
    return {"combo": tag, "arm": arm, "seed": seed, "gen_failures": fails, "rounds": rounds}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--arms", nargs="+", default=["control", "invert", "gated"])
    args = ap.parse_args()
    out = [run_arm(a, args.seed) for a in args.arms]
    tag = "pilot" if set(args.arms) == {"control", "invert", "gated"} else "pilot-noisy"
    with open(OUT / f"{tag}_seed{args.seed}.json", "w") as f:
        json.dump({"block": tag, "combos": out}, f, indent=1)
    print(f"Wrote {tag}_seed{args.seed}.json")


if __name__ == "__main__":
    main()

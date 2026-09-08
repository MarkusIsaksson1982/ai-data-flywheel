"""
AI Data Flywheel — lightweight text simulation
================================================
Domain: short chain-of-thought (CoT) traces + final answers for
elementary-to-intermediate math / logic problems (rule-verifiable).

Loop per round:
  1. Choose teacher SM version(s) + artifact sets (lineage mix).
  2. "Train" new SM = update small param vector + prompt template
     from selected high-quality artifacts (heuristic, no neural nets).
  3. Generate new artifacts with new SM.
  4. Evaluate: rule-based verifier (+ SM-as-judge from R2 on).
  5. Select high-quality subset to keep.
  6. Log metrics: quality, diversity, collapse signals.

Everything is stdlib-only, seeded, reproducible.
Run:  python flywheel_sim.py
Outputs: flywheel_log.json, round_summaries.txt (in same dir)
"""
from __future__ import annotations
import json
import random
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from statistics import mean, pstdev

# ----------------------------------------------------------------------------
# 0. Problem bank (ground truth known -> rule-verifiable evaluation)
# ----------------------------------------------------------------------------
PROBLEMS = [
    {"pid": "P01", "text": "Maya has 14 apples, buys 9 more, then gives away 7. How many left?", "answer": 16,
     "steps": ["14 + 9 = 23", "23 - 7 = 16"]},
    {"pid": "P02", "text": "A box holds 6 rows of 8 muffins. If 13 are eaten, how many remain?", "answer": 35,
     "steps": ["6 * 8 = 48", "48 - 13 = 35"]},
    {"pid": "P03", "text": "Solve: 3x + 7 = 31. What is x?", "answer": 8,
     "steps": ["3x = 31 - 7 = 24", "x = 24 / 3 = 8"]},
    {"pid": "P04", "text": "A train travels 60 km/h for 2.5 hours. How far (km)?", "answer": 150,
     "steps": ["60 * 2 = 120", "60 * 0.5 = 30", "120 + 30 = 150"]},
    {"pid": "P05", "text": "LCM-style: every 4th and 6th day events coincide. First coincide after day 0 is day?", "answer": 12,
     "steps": ["multiples of 4: 4, 8, 12", "multiples of 6: 6, 12", "first common = 12"]},
    {"pid": "P06", "text": "Rectangle 9 by 5. Perimeter?", "answer": 28,
     "steps": ["2 * (9 + 5) = 28"]},
    {"pid": "P07", "text": "Sara scored 82, 91, 77, 90. Average?", "answer": 85,
     "steps": ["82 + 91 + 77 + 90 = 340", "340 / 4 = 85"]},
    {"pid": "P08", "text": "If 5 workers build 5 sheds in 5 days, how many days for 10 workers to build 10 sheds?", "answer": 5,
     "steps": ["rate per worker holds constant", "work scales with workers, so time stays 5"]},
    {"pid": "P09", "text": "Next prime after 30?", "answer": 31,
     "steps": ["30 composite", "31 has no divisors except 1,31"]},
    {"pid": "P10", "text": "2^7 minus 100?", "answer": 28,
     "steps": ["2^7 = 128", "128 - 100 = 28"]},
    {"pid": "P11", "text": "A shop gives 20% off $45. Sale price?", "answer": 36,
     "steps": ["20% of 45 = 9", "45 - 9 = 36"]},
    {"pid": "P12", "text": "Sum of integers 1..20?", "answer": 210,
     "steps": ["n(n+1)/2 = 20*21/2", "20*21=420, /2=210"]},
]
PROBLEM_BY_ID = {p["pid"]: p for p in PROBLEMS}

# Phrasing templates (diversity source; models unlock more of them as they improve)
STEP_PHRASES = [
    "Compute: {s}.",
    "Next, {s}.",
    "So {s}, carrying forward.",
    "Check: {s}.",
    "Then {s}; looks consistent.",
]
WRONG_OP_SWAP = {"+": "-", "-": "+", "*": "+", "/": "-"}  # typical weak-model slip

ARITH_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)")


def safe_eval_step(expr: str):
    """Return (is_checkable, is_correct) for first 'a op b = c' found in expr."""
    m = ARITH_RE.search(expr)
    if not m:
        return False, True  # non-arithmetic prose: not checkable, don't penalize
    a, op, b, c = float(m.group(1)), m.group(2), float(m.group(3)), float(m.group(4))
    try:
        want = {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b != 0 else float("nan")}[op]
    except Exception:
        return True, False
    return True, abs(want - c) < 1e-6


# ----------------------------------------------------------------------------
# 1. Simulated Model (SM) representation
# ----------------------------------------------------------------------------
@dataclass
class SimulatedModel:
    version: str
    capability: str                      # short human-readable description
    params: dict                         # controllable skill vector
    prompt_template: str                 # generation policy in words
    lineage: dict                        # {"parent_models": [...], "data_rounds": [...], "n_source": int}
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def make_sm0() -> SimulatedModel:
    return SimulatedModel(
        version="SM-0",
        capability="Baseline: weak arithmetic, 1-2 step chains, sloppy format, no self-check.",
        params={"arithmetic_acc": 0.55, "reason_depth": 1.4, "format_rel": 0.70,
                "diversity": 0.60, "self_critique": 0.30, "temperature": 1.0,
                "misc_rate": 0.0, "trap_rate": 0.0, "compound_growth": 0.0,
                "tier_acc": [0.55, 0.55, 0.55]},  # per-tier skill; used only when
                # the problem carries a 'tier' key, else arithmetic_acc (legacy)
        prompt_template=("Solve step by step, then give 'Final: <number>'. "
                         "Keep it short."),
        lineage={"parent_models": [], "data_rounds": [], "n_source": 0},
        notes="Hand-designed baseline.",
    )


# ----------------------------------------------------------------------------
# 2. Generation: SM produces artifacts
# ----------------------------------------------------------------------------
def _corrupt_number(x: float, rng: random.Random) -> float:
    delta = rng.choice([-3, -2, -1, 1, 2, 3, 10, -10])
    return x + delta


MISC_DELTA = 1  # deterministic wrong-answer offset per misconception firing


def _misc_artifact(sm: SimulatedModel, problem: dict, aid: str, rnd: int) -> dict:
    """Deterministic fluent-but-wrong artifact: same wrong answer every firing,
    fixed 'Compute:' phrasing, well-formed Final line. Enables coordinated
    wrong-answer mode-lock tests (perturbation noise cannot coordinate)."""
    cot = []
    for s in problem["steps"]:
        ms = list(ARITH_RE.finditer(s))
        if ms:
            mm = ms[-1]
            bad = float(mm.group(4)) + MISC_DELTA
            bad_s = str(int(bad)) if bad.is_integer() else str(round(bad, 2))
            s = s[:mm.start(4)] + bad_s + s[mm.end(4):]
        cot.append(f"Compute: {s}.")
    ans = problem["answer"] + MISC_DELTA
    return {
        "id": aid, "round": rnd, "model_version": sm.version,
        "problem_id": problem["pid"], "problem_text": problem["text"],
        "cot": cot, "final_line": f"Final: {ans}", "final_answer": ans,
        "ground_truth": problem["answer"], "_misc": True,
        "lineage": {"model": sm.version,
                    "model_parents": list(sm.lineage.get("parent_models", [])),
                    "model_data_rounds": list(sm.lineage.get("data_rounds", []))},
    }


def generate_artifact(sm: SimulatedModel, problem: dict, aid: str, rnd: int,
                      rng: random.Random) -> dict:
    p = sm.params
    # Systematic misconception: a deterministic wrong rule (result numbers +1,
    # fixed phrasing, fluent format) that fires with prob misc_rate. Guarded so
    # legacy streams (misc_rate 0) draw no RNG and behave bit-identically.
    if p.get("misc_rate", 0.0) > 0.0 and rng.random() < p["misc_rate"]:
        return _misc_artifact(sm, problem, aid, rnd)
    # how many canonical steps to attempt (weak models truncate chains)
    want_steps = max(1, min(len(problem["steps"]), round(rng.gauss(p["reason_depth"], 0.6))))
    # diversity: which phrasing pool is available (better models use more templates)
    pool = STEP_PHRASES[: max(2, int(len(STEP_PHRASES) * (0.4 + 0.6 * p["diversity"])))]
    cot, error_made = [], False
    # compounding errors (guarded): per-step accuracy decays geometrically with
    # step position, so long chains are disproportionately wrong — wrongness
    # coincides structurally with length. growth=0 reduces exactly (branched),
    # so legacy streams are bit-identical.
    growth = p.get("compound_growth", 0.0)
    # tier-specific skill (guarded): problems carrying a 'tier' key train and
    # test tier_acc[tier] independently (non-transferable skill); everything
    # else uses arithmetic_acc exactly as before (legacy, bit-identical).
    tier = problem.get("tier")
    acc_base = p["tier_acc"][tier] if (tier is not None and "tier_acc" in p) else p["arithmetic_acc"]
    for idx, s in enumerate(problem["steps"][:want_steps]):
        s_out = s
        acc_eff = acc_base * (1.0 - growth) ** idx if growth > 0.0 else acc_base
        if rng.random() > acc_eff:
            error_made = True
            if rng.random() < 0.5:
                # corrupt the result number
                m = ARITH_RE.search(s_out)
                if m:
                    bad = _corrupt_number(float(m.group(4)), rng)
                    bad_s = str(int(bad)) if float(bad).is_integer() else str(round(bad, 2))
                    s_out = s_out[:m.start(4)] + bad_s + s_out[m.end(4):]
                else:
                    s_out = s_out + " (approx?)"
            else:
                # swap operator
                for op, bad_op in WRONG_OP_SWAP.items():
                    if op in s_out:
                        s_out = s_out.replace(op, bad_op, 1)
                        break
        cot.append(rng.choice(pool).format(s=s_out))
    # truncated reasoning -> guess
    if want_steps < len(problem["steps"]) and rng.random() < 0.5:
        error_made = True
    # final answer
    if error_made and rng.random() < 0.85:
        ans = problem["answer"] + rng.choice([-3, -2, -1, 1, 2, 3, 5, -5, 10])
        # keep int-like
        ans = int(ans)
    else:
        ans = problem["answer"]
    # format slip
    if rng.random() > p["format_rel"]:
        final_line = f"answer is about {ans}??"  # malformed
    else:
        final_line = f"Final: {ans}"
    # temperature: high temp occasionally adds rambling distractor step
    if rng.random() < (p["temperature"] - 0.7) * 0.25:
        cot.insert(rng.randrange(len(cot) + 1), rng.choice(
            ["Hmm, let me think differently.", "Alternatively, estimate roughly.",
             "Double-check units before proceeding."]))
        # fluency trap (guarded): rambling can derail the final answer while
        # leaving the format well-formed. Draws RNG only when a distractor was
        # inserted AND trap_rate > 0, so legacy streams are bit-identical.
        if p.get("trap_rate", 0.0) > 0.0 and rng.random() < p["trap_rate"]:
            ans = int(ans + rng.choice([-5, -3, -2, 2, 3, 5]))
            final_line = f"Final: {ans}"  # stays fluent: the trap
    return {
        "id": aid, "round": rnd, "model_version": sm.version,
        "problem_id": problem["pid"], "problem_text": problem["text"],
        "cot": cot, "final_line": final_line, "final_answer": ans,
        "ground_truth": problem["answer"], "_misc": False,
        "lineage": {"model": sm.version,
                    "model_parents": list(sm.lineage.get("parent_models", [])),
                    "model_data_rounds": list(sm.lineage.get("data_rounds", []))},
    }


def generate_batch(sm: SimulatedModel, rnd: int, n_per_problem: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    arts = []
    k = 0
    # shuffle problem order for realism
    probs = PROBLEMS * n_per_problem
    rng.shuffle(probs)
    for prob in probs:
        k += 1
        arts.append(generate_artifact(sm, prob, f"R{rnd}-{sm.version}-{k:03d}", rnd, rng))
    return arts


# ----------------------------------------------------------------------------
# 3. Evaluation — rule-based verifier + (from R2) SM-as-judge
# ----------------------------------------------------------------------------
def rule_evaluate(art: dict) -> dict:
    correct = 1.0 if art["final_answer"] == art["ground_truth"] else 0.0
    checks = [safe_eval_step(s) for s in art["cot"]]
    checkable = [c for checkable, c in checks if checkable]
    step_cons = (sum(1 for c in checkable if c) / len(checkable)) if checkable else 0.5
    fmt = 1.0 if re.search(r"Final:\s*-?\d+", art["final_line"]) else 0.0
    # conciseness: 1-4 steps ideal
    n = len(art["cot"])
    conc = 1.0 if 1 <= n <= 4 else (0.6 if n <= 6 else 0.3)
    score = round(100 * (0.70 * correct + 0.15 * step_cons + 0.10 * fmt + 0.05 * conc), 1)
    parts = []
    parts.append("correct final" if correct else f"wrong final ({art['final_answer']} vs {art['ground_truth']})")
    parts.append(f"step-consistency {step_cons:.2f}")
    parts.append("format ok" if fmt else "format broken")
    return {"rule_score": score, "correct": bool(correct),
            "step_consistency": round(step_cons, 3), "format_ok": bool(fmt),
            "rationale": "; ".join(parts) + "."}


def sm_judge_score(rule_score: float, judge: SimulatedModel, rng: random.Random) -> float:
    """Noisy judge: noise shrinks as judge self_critique grows. Also slight optimism bias for weak judges."""
    q = judge.params["self_critique"]
    noise = rng.gauss(0, (1.05 - q) * 18)
    bias = (1 - q) * 4  # weak judges are a bit generous
    return round(max(0, min(100, rule_score + bias + noise)), 1)


def evaluate_batch(arts: list[dict], judge: SimulatedModel | None,
                   alpha_rule: float, seed: int) -> list[dict]:
    rng = random.Random(seed)
    for a in arts:
        r = rule_evaluate(a)
        a.update(r)
        if judge is None:
            a["judge_version"], a["judge_score"], a["final_score"] = None, None, r["rule_score"]
            a["eval_mix"] = "rule-only (author-designed verifier)"
        else:
            js = sm_judge_score(r["rule_score"], judge, rng)
            final = round(alpha_rule * r["rule_score"] + (1 - alpha_rule) * js, 1)
            a["judge_version"], a["judge_score"], a["final_score"] = judge.version, js, final
            a["eval_mix"] = f"{int(alpha_rule*100)}% rule + {int((1-alpha_rule)*100)}% {judge.version}-as-judge"
            a["rationale"] += f" SM-judge {judge.version} said {js}."
    return arts


# ----------------------------------------------------------------------------
# 4. "Training": heuristic update from selected artifacts
# ----------------------------------------------------------------------------
def select_kept(arts: list[dict], thresh: float = 70.0, top_frac: float | None = None) -> list[dict]:
    ranked = sorted(arts, key=lambda a: a["final_score"], reverse=True)
    if top_frac is not None:
        k = max(1, int(len(ranked) * top_frac))
        return ranked[:k]
    return [a for a in ranked if a["final_score"] >= thresh]


def train_next_sm(new_version: str, parents: list[SimulatedModel], kept: list[dict],
                  data_rounds: list[int], lr: float = 0.45,
                  temp_override: float | None = None, lesson: str = "") -> SimulatedModel:
    """Move params toward observed traits of kept set (distillation heuristic)."""
    base = parents[-1]  # primary parent for params
    old = base.params
    if kept:
        corr_rate = mean(1.0 if a["correct"] else 0.0 for a in kept)
        fmt_rate = mean(1.0 if a["format_ok"] else 0.0 for a in kept)
        avg_steps = mean(len(a["cot"]) for a in kept)
        avg_judge_agree = mean(a["step_consistency"] for a in kept)
    else:  # total collapse fallback: regress slightly
        corr_rate, fmt_rate, avg_steps, avg_judge_agree = 0.3, 0.5, 1.0, 0.3
    new = dict(old)
    new["arithmetic_acc"] = round((1 - lr) * old["arithmetic_acc"] + lr * (0.35 + 0.65 * corr_rate), 3)
    new["format_rel"] = round((1 - lr) * old["format_rel"] + lr * (0.30 + 0.70 * fmt_rate), 3)
    # reasoning depth chases successful chain length, capped
    target_depth = max(1.0, min(3.2, avg_steps + (0.3 if corr_rate > 0.6 else -0.2)))
    new["reason_depth"] = round((1 - lr) * old["reason_depth"] + lr * target_depth, 3)
    new["self_critique"] = round(min(0.95, (1 - lr) * old["self_critique"] + lr * (0.3 + 0.7 * avg_judge_agree)), 3)
    # misconception inheritance: selecting _misc artifacts raises next gen's rate
    # (the feedback loop behind lock-in); .get keeps old saved models compatible.
    misc_frac = mean(1.0 if a.get("_misc") else 0.0 for a in kept) if kept else 0.0
    new["misc_rate"] = round((1 - lr) * old.get("misc_rate", 0.0) + lr * misc_frac, 3)
    # tier skills (guarded): practiced tiers learn from own-tier kept via the same
    # distillation rule; unpracticed tiers forget toward 0.30 (-0.08/round, floored)
    # — the use-it-or-lose-it mechanism behind curriculum effects. Skipped unless
    # the model carries tier_acc AND kept artifacts carry tier keys (legacy untouched).
    if "tier_acc" in old and kept and any(a.get("tier") is not None for a in kept):
        new_acc = []
        for t in range(len(old["tier_acc"])):
            sub = [a for a in kept if a.get("tier") == t]
            if sub:
                c = mean(1.0 if a["correct"] else 0.0 for a in sub)
                new_acc.append(round((1 - lr) * old["tier_acc"][t] + lr * (0.35 + 0.65 * c), 3))
            else:
                new_acc.append(round(max(0.30, old["tier_acc"][t] - 0.08), 3))
        new["tier_acc"] = new_acc
    # diversity: exploit (shrink) vs explore handled by caller via temp/diversity nudge
    new["diversity"] = old["diversity"]
    new["temperature"] = temp_override if temp_override is not None else max(0.55, old["temperature"] * 0.96)
    # prompt template inherits + appends distilled lesson from best artifact
    best = max(kept, key=lambda a: a["final_score"]) if kept else None
    distilled = lesson or (f"Lesson from {best['id']}: recompute each 'a op b = c' before final."
                           if best else "No lesson (empty kept set).")
    new_template = base.prompt_template + " " + distilled
    cap = (f"Trained on {len(kept)} kept arts from rounds {data_rounds}; "
           f"acc~{new['arithmetic_acc']}, depth~{new['reason_depth']}, fmt~{new['format_rel']}.")
    return SimulatedModel(version=new_version, capability=cap, params=new,
                          prompt_template=new_template,
                          lineage={"parent_models": [p.version for p in parents],
                                   "data_rounds": list(data_rounds), "n_source": len(kept)},
                          notes=distilled)


# ----------------------------------------------------------------------------
# 5. Metrics (quality + diversity/collapse indicators)
# ----------------------------------------------------------------------------
def diversity_metrics(arts: list[dict]) -> dict:
    # lexical diversity: unique phrasing-pattern proxy via first-7-chars of each step
    pats = [s[:14] for a in arts for s in a["cot"]]
    pat_div = len(set(pats)) / max(1, len(pats))
    # answer spread per problem (want 1 distinct answer AND it being correct)
    by_prob: dict[str, set] = {}
    for a in arts:
        by_prob.setdefault(a["problem_id"], set()).add(a["final_answer"])
    avg_spread = round(mean(len(v) for v in by_prob.values()), 3)
    # pairwise Jaccard on token sets (sample for speed)
    rng = random.Random(0)
    toks = [set(" ".join(a["cot"] + [a["final_line"]]).lower().split()) for a in arts]
    pairs = [(rng.randrange(len(toks)), rng.randrange(len(toks))) for _ in range(min(300, len(toks) * 4))]
    sims = []
    for i, j in pairs:
        if i == j:
            continue
        u = toks[i] | toks[j]
        sims.append(len(toks[i] & toks[j]) / max(1, len(u)))
    self_sim = round(mean(sims), 3) if sims else 0.0  # high self-sim => homogenization
    return {"pattern_diversity": round(pat_div, 3), "avg_answer_spread_per_problem": avg_spread,
            "self_similarity": self_sim}


def round_metrics(arts: list[dict]) -> dict:
    return {"n": len(arts),
            "avg_final": round(mean(a["final_score"] for a in arts), 2),
            "avg_rule": round(mean(a["rule_score"] for a in arts), 2),
            "correct_rate": round(mean(1.0 if a["correct"] else 0.0 for a in arts), 3),
            "stdev": round(pstdev(a["final_score"] for a in arts), 2) if len(arts) > 1 else 0.0,
            **diversity_metrics(arts)}


# ----------------------------------------------------------------------------
# 6. Experiment driver with explicit lineage plan per round
# ----------------------------------------------------------------------------
# Each entry: which prior rounds supply data, alpha_rule (eval mix), judge, select rule.
PLAN = [
    # rnd, new SM, parents, data_rounds, n_per_prob, alpha, judge, select, temp, note
    dict(rnd=0, sm="SM-0", parents=[], data=[], npp=3, alpha=1.0, judge=None,
         select=("thresh", 70), temp=None, note="Setup baseline."),
    dict(rnd=1, sm="SM-1", parents=["SM-0"], data=[0], npp=3, alpha=1.0, judge=None,
         select=("thresh", 70), temp=None, note="Naive flywheel: train on R0 top."),
    dict(rnd=2, sm="SM-2", parents=["SM-1"], data=[1], npp=3, alpha=0.7, judge="SM-1",
         select=("topfrac", 0.5), temp=None, note="Recent-only + first SM-as-judge (70/30)."),
    dict(rnd=3, sm="SM-3", parents=["SM-2"], data=[0, 1, 2], npp=3, alpha=0.6, judge="SM-2",
         select=("topfrac", 0.5), temp=None, note="Cumulative data; 60/40 eval."),
    dict(rnd=4, sm="SM-4", parents=["SM-3"], data=[0, 1, 3], npp=3, alpha=0.6, judge="SM-2",
         select=("topfrac", 0.5), temp=None, note="Selective reuse: SKIP R2 (suspected drift), reuse R0+R1+R3."),
    dict(rnd=5, sm="SM-5a", parents=["SM-4"], data=[3, 4], npp=2, alpha=0.5, judge="SM-4",
         select=("topfrac", 0.4), temp=0.55, note="Parallel exploit branch: low temp, strict top-40%."),
    dict(rnd=5, sm="SM-5b", parents=["SM-4"], data=[0, 3, 4], npp=2, alpha=0.5, judge="SM-4",
         select=("topfrac", 0.7), temp=1.15, note="Parallel explore branch: high temp, loose top-70%."),
    dict(rnd=6, sm="SM-6", parents=["SM-5a", "SM-5b"], data=[4, 5], npp=3, alpha=0.5, judge="SM-4",
         select=("topfrac", 0.5), temp=0.8, note="Distill best of both R5 branches."),
]

OUT = Path(__file__).parent


def main():
    seed_base = 20260907
    models: dict[str, SimulatedModel] = {"SM-0": make_sm0()}
    rounds_data: dict[int, list[dict]] = {}
    kept_by_round: dict[int, list[dict]] = {}
    summaries = []
    # group PLAN by rnd preserving parallel branches
    from collections import defaultdict
    by_round: dict[int, list[dict]] = defaultdict(list)
    for step in PLAN:
        by_round[step["rnd"]].append(step)

    for rnd in sorted(by_round):
        for step in by_round[rnd]:
            ver = step["sm"]
            if rnd == 0:
                sm = models[ver]
            else:
                parents = [models[v] for v in step["parents"]]
                pool = [a for r in step["data"] for a in kept_by_round.get(r, [])]
                # parallel R5 branches need distinct diversity nudges
                extra = ""
                div_nudge = 0.0
                if ver == "SM-5a":
                    extra = "Exploit: prefer terse proven patterns."
                elif ver == "SM-5b":
                    extra = "Explore: vary phrasing and step order."
                elif ver == "SM-6":
                    extra = "Distilled from exploit+explore winners: keep terse correct chains, drop rambling."
                sm = train_next_sm(ver, parents, pool, step["data"],
                                   temp_override=step["temp"], lesson=extra)
                if ver == "SM-5b":
                    sm.params["diversity"] = min(0.95, parents[-1].params["diversity"] + 0.15)
                if ver == "SM-5a":
                    sm.params["diversity"] = max(0.25, parents[-1].params["diversity"] - 0.15)
                models[ver] = sm
            judge = models[step["judge"]] if step["judge"] else None
            arts = generate_batch(sm, rnd if ver not in ("SM-5a", "SM-5b") else 5,
                                  step["npp"], seed_base + rnd * 100 + sum(ord(c) for c in ver) % 50)
            # tag branch
            for a in arts:
                a["branch"] = ver
            evaluate_batch(arts, judge, step["alpha"], seed_base + rnd * 7 + 3)
            kind, val = step["select"]
            kept = select_kept(arts, thresh=val) if kind == "thresh" else select_kept(arts, top_frac=val)
            for a in arts:
                a["kept"] = a["id"] in {k["id"] for k in kept}
            key = rnd if rnd != 5 else f"5-{ver}"
            rounds_data[key] = arts
            kept_by_round[key] = kept
            # R5 aggregate + R4-style numeric keys for later data reuse
            if rnd == 5:
                kept_by_round.setdefault(5, []).extend(kept)
                rounds_data.setdefault(5, []).extend(arts)
            m = round_metrics(arts)
            summaries.append({"round": rnd, "branch": ver, "note": step["note"],
                              "model": sm.to_dict(), "metrics": m,
                              "n_kept": len(kept),
                              "eval_mix": arts[0]["eval_mix"] if arts else ""})
            print(f"R{rnd} {ver}: n={m['n']} avg={m['avg_final']} corr={m['correct_rate']} "
                  f"kept={len(kept)} selfsim={m['self_similarity']} spread={m['avg_answer_spread_per_problem']}")

    # persist
    all_arts = [a for k in sorted(rounds_data, key=str) for a in rounds_data[k]
                if not (isinstance(k, str) and k.startswith("5-"))]  # avoid double-counting R5
    with open(OUT / "flywheel_log.json", "w") as f:
        json.dump({"models": {v: m.to_dict() for v, m in models.items()},
                   "round_summaries": summaries, "artifacts": all_arts}, f, indent=1)
    with open(OUT / "round_summaries.txt", "w") as f:
        for s in summaries:
            f.write(f"Round {s['round']} {s['branch']}: {s['note']}\n"
                    f"  metrics={s['metrics']} kept={s['n_kept']} eval={s['eval_mix']}\n"
                    f"  capability={s['model']['capability']}\n"
                    f"  template={s['model']['prompt_template'][:220]}...\n\n")
    print(f"\nWrote {OUT/'flywheel_log.json'} ({len(all_arts)} artifacts, {len(models)} models)")


if __name__ == "__main__":
    main()

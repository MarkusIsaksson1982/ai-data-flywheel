"""
Flywheel harness v3 — adversarial judges, chance-adjusted lock, multi-seed, scorer fix
======================================================================================
Four short-term follow-ups in one codebase (stdlib only):

A. ADVERSARIAL JUDGES (re-test alpha=0 for real). v2's blind judge was too
   faithful (corr>0.95), so pure0 changed nothing. New judge kinds add LARGE
   systematic bonuses on top of small noise (sd 5):
     adv_verbose: +3 per CoT step beyond 2 (cap +18) — rewards rambling.
     adv_fluent : +25 if (wrong final AND format_ok) — up-scores fluent errors.
     adv_surface: +6 per step starting with 'check:' (cap +18) — surface-form bias.
   Run at alpha=0 (pure) and alpha=0.5 (does a verifier anchor contain it?).

B. CHANCE-ADJUSTED MODE-LOCK. v2's per-pid max share fired everywhere (0.8-0.9
   even healthy: n=3-6 steps/pid over 6 template ids makes high shares likely).
   New: batch-level total-variation distance (TVD) of the template distribution
   from uniform over the 6 ids. Null reasoning: with n~100 steps, per-cell sd =
   sqrt(p(1-p)/n) ~ 0.037, E|dev| ~ 0.030, E[TVD] ~ 0.09. Threshold 0.25 sits
   ~4 sigma above chance — sampling noise cannot reach it. Persistence = same
   argmax template in consecutive rounds with TVD > 0.25. Plus a second lock
   channel that matters more here: wrong-answer mode share = max over pids of
   the largest kept-share behind one WRONG answer (lock-in on an error).

C. MULTI-SEED. v2 showed a universal G6->G7 quality dip under ONE shared seed.
   Thread seed_offset through generation + judge seeds; rerun the ramp subset
   (topk/floor_caps/coverage_grid x blind/fixed05/simple) at offsets 0/1500/3000.

D. SCORER FIX ('fixed' vs 'legacy'). Legacy: first-regex-match arithmetic only,
   default 0.5 when nothing checkable -> ~7pt handicap on prose-step categories
   (P05/P08/P09) and false penalties on multi-add chains. Fixed scorer:
     1. try full-LHS safe expression eval first (ast-based, ^ mapped to **,
        letters/calls/names rejected) so '82+91+77+90=340' and '2*(9+5)=28'
        verify correctly;
     2. fall back to ALL regex matches in the step (step correct iff every
        matched equation holds), covering '3x = 31-7 = 24' style steps;
     3. default 1.0 (not 0.5) when nothing is checkable — don't penalize what
        you can't verify (residual risk: truncated-but-correct chains still
        score high; completeness remains unmeasured — documented).
   Weights shift 70/15/10/5 -> 65/20/10/5 (more weight on reasoning now fair).
   Compare legacy vs fixed on topk/floor_caps x blind/fixed05/simple.

Usage: python flywheel_harness3.py --block adv|seed|scorer|sanity|all
Out: harness3_{block}.json (+ console log if redirected).
"""
from __future__ import annotations
import argparse
import ast
import json
import math
import random
import re
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness2 as h2

OUT = Path(__file__).parent
NPP = 3
BASE_SEED = 20260907
POOL_CAP = 36
PHASE_OF = {0: "normal", 1: "normal", 2: "normal", 3: "collapse",
            4: "collapse", 5: "collapse", 6: "recovery", 7: "recovery"}
N_TMPL = 6  # 5 phrasing templates + distractor/unknown
TVD_THRESH = 0.25

# ----------------------------------------------------------------------------
# D. Fixed scorer
# ----------------------------------------------------------------------------
_SAFE_CHARS = set("0123456789+-*/(). %^")


def _safe_eval_lhs(lhs: str):
    """Evaluate a pure-arithmetic LHS with proper precedence. None if rejected."""
    s = lhs.strip().replace("^", "**")  # bank uses ^ for exponent
    if not s or any(c not in _SAFE_CHARS for c in s):
        return None
    try:
        tree = ast.parse(s, mode="eval")
    except Exception:
        return None
    banned = (ast.Name, ast.Call, ast.Attribute, ast.Subscript, ast.BitXor,
              ast.LShift, ast.RShift, ast.Invert)
    if any(isinstance(n, banned) for n in ast.walk(tree)):
        return None
    try:
        return eval(compile(tree, "<lhs>", "eval"), {"__builtins__": {}}, {})  # noqa: S307
    except Exception:
        return None


def _rhs_number(rhs: str):
    m = re.search(r"-?\d+(?:\.\d+)?", rhs)
    return float(m.group(0)) if m else None


def step_check_v3(step: str):
    """Return (checkable, correct) under the fixed scorer."""
    if "=" in step:
        lhs, rhs = step.rsplit("=", 1)
        want = _rhs_number(rhs)
        if want is not None:
            got = _safe_eval_lhs(lhs)
            if got is not None:
                try:
                    return True, abs(float(got) - want) < 1e-6
                except Exception:
                    return True, False
        # fallback: every single-op equation mentioned must hold
        ms = list(base.ARITH_RE.finditer(step))
        if ms:
            ok = True
            for mm in ms:
                a, op, bb, cc = float(mm.group(1)), mm.group(2), float(mm.group(3)), float(mm.group(4))
                try:
                    exp = {"+": a + bb, "-": a - bb, "*": a * bb,
                           "/": a / bb if bb != 0 else float("nan")}[op]
                except Exception:
                    ok = False
                    break
                if abs(exp - cc) >= 1e-6:
                    ok = False
            return True, ok
        return False, True
    # no '=' at all: prose or remark -> not verifiable, no penalty
    return False, True


def rule_evaluate_v3(art: dict, scorer: str = "legacy") -> dict:
    if scorer == "legacy":
        d = base.rule_evaluate(art)
        d["scorer"] = "legacy"
        return d
    correct = 1.0 if art["final_answer"] == art["ground_truth"] else 0.0
    checks = [step_check_v3(s) for s in art["cot"]]
    checkable = [c for chk, c in checks if chk]
    # FIX: default 1.0 (no penalty) when nothing is verifiable
    step_cons = (sum(1 for c in checkable if c) / len(checkable)) if checkable else 1.0
    fmt = 1.0 if re.search(r"Final:\s*-?\d+", art["final_line"]) else 0.0
    n = len(art["cot"])
    conc = 1.0 if 1 <= n <= 4 else (0.6 if n <= 6 else 0.3)
    score = round(100 * (0.65 * correct + 0.20 * step_cons + 0.10 * fmt + 0.05 * conc), 1)
    parts = [("correct final" if correct else f"wrong final ({art['final_answer']} vs {art['ground_truth']})"),
             f"step-consistency {step_cons:.2f}", ("format ok" if fmt else "format broken")]
    return {"rule_score": score, "correct": bool(correct),
            "step_consistency": round(step_cons, 3), "format_ok": bool(fmt),
            "rationale": "; ".join(parts) + ".", "scorer": "fixed"}


def scorer_sanity() -> list[str]:
    """Check every bank canonical step + a corrupted twin under both scorers."""
    lines = []
    for p in base.PROBLEMS:
        for s in p["steps"]:
            leg = base.safe_eval_step(s)
            fix = step_check_v3(s if "=" in s else s + " = 0")
            # corrupted twin: bump the last result number by +2 where possible
            m = list(base.ARITH_RE.finditer(s))
            twin = ("n/a (non-regex step)", None)
            if m:
                mm = m[-1]
                bad = float(mm.group(4)) + 2
                bads = str(int(bad)) if bad.is_integer() else str(round(bad, 2))
                t = s[:mm.start(4)] + bads + s[mm.end(4):]
                twin = (t, step_check_v3(t))
            lines.append(f"{p['pid']}: {s!r} legacy={leg} fixed={fix} | twin={twin[0]!r}->{twin[1]}")
    return lines


# ----------------------------------------------------------------------------
# A. Adversarial judges
# ----------------------------------------------------------------------------
def adv_bonus(kind: str, art: dict) -> float:
    if kind == "adv_verbose":
        return min(18.0, 3.0 * max(0, len(art["cot"]) - 2))
    if kind == "adv_fluent":
        return 25.0 if (not art["correct"] and art["format_ok"]) else 0.0
    if kind == "adv_surface":
        n = sum(1 for s in art["cot"] if s.strip().lower().startswith("check:"))
        return min(18.0, 6.0 * n)
    raise ValueError(kind)


def evaluate_v3(arts, judge_sm, kind, alpha, seed, calib, scorer):
    rng = random.Random(seed)
    for a in arts:
        r = rule_evaluate_v3(a, scorer)
        a.update(r)
        raw = h1._blind_raw(r["rule_score"], judge_sm, rng)
        if kind == "blind":
            j = round(raw, 1)
        elif kind == "verifier_assisted":
            j = round(0.6 * r["rule_score"] + 0.4 * raw, 1)
        elif kind == "calibrated":
            ac, bc = calib
            j = round(max(0, min(100, ac * raw + bc)), 1)
        elif kind in ("adv_verbose", "adv_fluent", "adv_surface"):
            j = round(max(0, min(100, raw + adv_bonus(kind, a) + rng.gauss(0, 5))), 1)
        else:
            raise ValueError(kind)
        a["judge_version"], a["judge_score"] = judge_sm.version, j
        a["judge_kind"], a["alpha_rule"] = kind, alpha
        a["final_score"] = round(alpha * r["rule_score"] + (1 - alpha) * j, 1)
        a["eval_mix"] = f"{kind} alpha={alpha} scorer={scorer}"
        a["rationale"] += f" Judge({kind},{judge_sm.version})={j}."


def golden_for(scorer):
    sm0 = base.make_sm0()
    rng = random.Random(999)
    arts = [base.generate_artifact(sm0, p, f"GOLD-{i:02d}", -1, rng)
            for i, p in enumerate(base.PROBLEMS * 2)]
    for a in arts:
        a.update(rule_evaluate_v3(a, scorer))
    return arts


# ----------------------------------------------------------------------------
# B. Chance-adjusted mode lock (batch template TVD + wrong-answer mode)
# ----------------------------------------------------------------------------
def template_tvd(arts: list[dict]) -> tuple[float, int | None]:
    tids = [h2.template_id(s) for a in arts for s in a["cot"]]
    n = len(tids)
    if n == 0:
        return 0.0, None
    c = Counter(tids)
    tvd = round(0.5 * sum(abs(c.get(t, 0) / n - 1.0 / N_TMPL) for t in range(N_TMPL)), 3)
    dom = c.most_common(1)[0][0]
    return tvd, dom


def wrong_answer_mode(kept: list[dict]) -> dict:
    by_pid: dict[str, list[dict]] = {}
    for a in kept:
        by_pid.setdefault(a["problem_id"], []).append(a)
    best = {"pid": None, "share": 0.0, "answer": None}
    for pid, items in by_pid.items():
        wrong = [a for a in items if not a["correct"]]
        if not wrong:
            continue
        w, cnt = Counter(a["final_answer"] for a in wrong).most_common(1)[0]
        share = round(cnt / len(items), 3)
        if share > best["share"]:
            best = {"pid": pid, "share": share, "answer": w}
    return best


# ----------------------------------------------------------------------------
# Driver (ramp protocol, seed threading, scorer + judge variants)
# ----------------------------------------------------------------------------
def run_combo(policy, judge_kind, alpha_mode, import_mode, scorer, seed_offset):
    tag = f"{policy}x{judge_kind}x{alpha_mode}x{import_mode}x{sctr(scorer)}xseed{seed_offset}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    kept_hist: list = []
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    calib = h1._fit_affine(
        [h1._blind_raw(a["rule_score"], sm, random.Random(777)) for a in golden_for(scorer)],
        [a["rule_score"] for a in golden_for(scorer)])
    lock_streak, prev_dom = 0, None
    for g in range(8):
        phase = h2.PHASE_OF[g]
        gs, js = BASE_SEED + seed_offset + g * 100, BASE_SEED + seed_offset + g * 7 + 11
        arts = base.generate_batch(sm, g, NPP, gs)
        if g == 0:
            for a in arts:
                a.update(rule_evaluate_v3(a, scorer))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": f"rule-only R0 scorer={scorer}",
                          "judge_kind": None, "alpha_rule": None})
        else:
            if judge_kind == "calibrated":
                gl = golden_for(scorer)
                jr = random.Random(777)
                calib = h1._fit_affine([h1._blind_raw(x["rule_score"], sm, jr) for x in gl],
                                       [x["rule_score"] for x in gl])
            if alpha_mode == "pure0":
                alpha = 0.0
            elif alpha_mode == "gated097":
                alpha = 0.8 if (prev_corr is not None and
                                (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            else:
                alpha = 0.5
            evaluate_v3(arts, sm, judge_kind, alpha, js, calib, scorer)
        if phase == "collapse":
            kept = h1.sel_topk(arts, kept_hist, k=h2.RAMP_KS[g])
            sel_name = f"topk-{h2.RAMP_KS[g]} (ramp)"
        else:
            kept = h1.POLICIES[policy](arts, kept_hist)
            sel_name = policy + ("+util-import" if phase == "recovery" and import_mode == "utility" else "")
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"] = a["id"] in kid
            a["phase"], a["combo"], a["seed_offset"] = phase, tag, seed_offset
        m = h1.compute_round_metrics(arts, kept)
        tvd, dom = template_tvd(arts)
        m["template_tvd"], m["tvd_dom_template"] = tvd, dom
        if tvd > TVD_THRESH and dom == prev_dom:
            lock_streak += 1
        elif tvd > TVD_THRESH:
            lock_streak = 1
        else:
            lock_streak = 0
        prev_dom = dom
        m["tvd_lock_persistence"] = lock_streak
        m["wrong_answer_mode"] = wrong_answer_mode(kept)
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        nxt = None
        if g < 7:
            nphase = h2.PHASE_OF[g + 1]
            if nphase == "collapse":
                pool, temp = kept, h2.RAMP_TEMPS[g + 1]
            elif nphase == "recovery":
                pool = h2.simple_pool(kept_hist + [kept], g + 1) if import_mode == "simple" \
                    else h2.utility_pool(kept_hist + [kept], g + 1)
                temp = 0.90
            else:
                pool, temp = kept, 0.85
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [g], temp_override=temp,
                                     lesson=f"[{phase}->{nphase}|{sel_name}|{judge_kind}/{alpha_mode}|{scorer}]")
            if nphase == "collapse":
                nxt.params["diversity"] = max(0.2, sm.params["diversity"] - 0.10)
        rounds_out.append({"g": g, "phase": phase, "selection": sel_name,
                           "alpha": arts[0].get("alpha_rule"), "calib": calib,
                           "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        kept_hist.append(kept)
        sm = nxt if nxt else sm
        print(f"{tag} G{g} [{phase}/{sel_name} a={arts[0].get('alpha_rule')}]: "
              f"corr={m['correct_rate']} cov={m['category_coverage']} tvd={tvd}(#{dom})+{lock_streak} "
              f"wrongmode={m['wrong_answer_mode']} jcorr={m['judge_corr']} bias={m['leniency_bias']}", flush=True)
    base_cov = min(rounds_out[1]["metrics"]["category_coverage"],
                   rounds_out[2]["metrics"]["category_coverage"])
    base_q = min(rounds_out[1]["metrics"]["correct_rate"],
                 rounds_out[2]["metrics"]["correct_rate"])
    fin = rounds_out[7]["metrics"]
    rec_time = next((i - 5 for i in (6, 7)
                     if rounds_out[i]["metrics"]["category_coverage"] - base_cov >= 0
                     and rounds_out[i]["metrics"]["correct_rate"] - (base_q - 0.05) >= 0), None)
    return {"combo": tag, "policy": policy, "judge": judge_kind, "alpha_mode": alpha_mode,
            "import_mode": import_mode, "scorer": scorer, "seed_offset": seed_offset,
            "baseline_cov": base_cov, "baseline_q": base_q,
            "cov_margin": round(fin["category_coverage"] - base_cov, 3),
            "q_margin": round(fin["correct_rate"] - (base_q - 0.05), 3),
            "recovery_time": rec_time, "recovery_success": rec_time is not None,
            "rounds": rounds_out}


def sctr(s):
    return "leg" if s == "legacy" else "fix"


BLOCKS = {
    "adv": [(p, j, a, "simple", "legacy", 0)
            for p in ["topk", "coverage_grid"]
            for j, a in [("adv_verbose", "pure0"), ("adv_fluent", "pure0"),
                         ("adv_surface", "pure0"), ("adv_fluent", "fixed05")]],
    "seed": [(p, "blind", "fixed05", "simple", "legacy", o)
             for p in ["topk", "floor_caps", "coverage_grid"] for o in [0, 1500, 3000]],
    "scorer": [(p, "blind", "fixed05", "simple", s, 0)
               for p in ["topk", "floor_caps"] for s in ["legacy", "fixed"]],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=["adv", "seed", "scorer", "sanity", "all"], default="all")
    args = ap.parse_args()
    if args.block in ("sanity", "all"):
        print("=== scorer sanity: canonical vs corrupted-twin per bank step ===")
        for line in scorer_sanity():
            print(line)
        # hard assertions on the headline fixes
        assert step_check_v3("82 + 91 + 77 + 90 = 340") == (True, True), "multi-add must verify"
        assert step_check_v3("2 * (9 + 5) = 28") == (True, True), "paren expr must verify"
        assert step_check_v3("2^7 = 128") == (True, True), "caret power must verify"
        assert step_check_v3("82 + 91 + 77 + 90 = 341")[1] is False, "corrupted chain must fail"
        assert step_check_v3("Hmm, let me think differently.") == (False, True), "prose stays neutral"
        print("sanity assertions passed.")
        if args.block == "sanity":
            return
    blocks = BLOCKS if args.block == "all" else {args.block: BLOCKS[args.block]}
    for name, combos in blocks.items():
        print(f"--- block {name}: {len(combos)} combos ---")
        results = [run_combo(*c) for c in combos]
        with open(OUT / f"harness3_{name}.json", "w") as f:
            json.dump({"block": name, "combos": results}, f, indent=1)
        print(f"Wrote harness3_{name}.json")


if __name__ == "__main__":
    main()

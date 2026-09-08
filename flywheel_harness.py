"""
Flywheel experimental harness — Threads A (collapse) + B (evaluator design)
===========================================================================
Builds on flywheel_sim.py (reuses SM representation, generation, rule
verifier, train_next_sm). Adds:

  1. Shared metric suite (quality / diversity / collapse / judge reliability)
  2. Interchangeable selection policies
  3. Judge variants (blind / verifier-assisted / calibrated + gated mixing)
  4. Protocol per combo: normal (R0-R2) -> induced collapse (R3-R4)
     -> recovery with historical re-import (R5-R6)

Run:  python flywheel_harness.py
Out:  harness_results.json, harness_report.md  (same dir)

Stdlib only. Seeded; generation/judge seeds are SHARED across combos so
differences reflect policy/judge, not sampling luck.
"""
from __future__ import annotations
import json
import math
import random
from collections import Counter
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base  # reuse domain, SM, generation, verifier, training

OUT = Path(__file__).parent
NPP = 3                       # 3 per problem x 12 problems = 36 arts/round
N_CATS = len(base.PROBLEMS)   # category == problem id (12 categories)
K_TARGET = 18                 # normal kept-set size target
COLLAPSE_K = 8                # induced-collapse kept size (strict top-k)
FLOOR, CAP_PER_PID, MIN_KEPT = 70.0, 2, 12

# ----------------------------------------------------------------------------
# 0. Previous-implementation recap (what we reuse vs add)
# ----------------------------------------------------------------------------
# Reused unchanged: PROBLEMS bank, SimulatedModel dataclass + make_sm0(),
# generate_artifact(), rule_evaluate() (70/15/10/5 weighting), train_next_sm()
# (param drift toward kept-set traits, lr=0.45), STEP_PHRASES / corruption model.
# Fixed in harness: nothing in base is monkey-patched; the known multi-add
# scorer blind spot (e.g. "82+91+77+90=340" parsed as "77+90=340") is KEPT so
# results stay comparable, and is documented as a limitation again.
# Added here: metric suite, selection policies, judge variants, protocol driver.

# ----------------------------------------------------------------------------
# 1. Shared metric suite
# ----------------------------------------------------------------------------
def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 3)


def _entropy_norm(counts: Counter, n_cats: int) -> float:
    tot = sum(counts.values())
    if tot == 0:
        return 0.0
    ent = -sum((c / tot) * math.log(c / tot) for c in counts.values())
    return round(ent / math.log(n_cats), 3)  # 0..1


def _cot_sig(a: dict) -> str:
    return " || ".join(s.strip().lower() for s in a["cot"]) + f" ## {a['final_answer']}"


def compute_round_metrics(arts: list[dict], kept: list[dict]) -> dict:
    """Full suite. Quality/diversity on batch; selection-shape on kept set."""
    kept_ids = {a["id"] for a in kept}
    # -- quality (full batch) --
    correct_rate = round(mean(1.0 if a["correct"] else 0.0 for a in arts), 3)
    verifier_pass = round(mean(1.0 if a["rule_score"] >= 70 else 0.0 for a in arts), 3)
    avg_final = round(mean(a["final_score"] for a in arts), 2)
    avg_rule = round(mean(a["rule_score"] for a in arts), 2)
    # -- diversity of kept set --
    pids = [a["problem_id"] for a in kept]
    cov = round(len(set(pids)) / N_CATS, 3) if kept else 0.0
    ent = _entropy_norm(Counter(pids), N_CATS)
    forgotten = sorted({p["pid"] for p in base.PROBLEMS} - set(pids))
    sigs = [_cot_sig(a) for a in kept]
    dup = round(1 - len(set(sigs)) / len(sigs), 3) if sigs else 1.0
    # pattern diversity over batch steps (comparable w/ base sim)
    pats = [s[:14] for a in arts for s in a["cot"]]
    pat_div = round(len(set(pats)) / max(1, len(pats)), 3)
    # dominant-pattern share (mode lock strength) over batch
    pc = Counter(pats)
    dom_pat, dom_share = (pc.most_common(1)[0][0], round(pc.most_common(1)[0][1] / len(pats), 3)) if pats else ("", 0.0)
    # -- judge reliability (batch) --
    js = [(a["judge_score"], a["rule_score"]) for a in arts if a.get("judge_score") is not None]
    if js:
        corr = _pearson([j for j, _ in js], [r for _, r in js])
        bias = round(mean(j - r for j, r in js), 2)
    else:
        corr, bias = None, None
    return {
        "n": len(arts), "n_kept": len(kept),
        "correct_rate": correct_rate, "verifier_pass_rate": verifier_pass,
        "avg_final": avg_final, "avg_rule": avg_rule,
        "category_coverage": cov, "selection_entropy": ent,
        "category_forgetting_n": len(forgotten), "category_forgetting": forgotten,
        "duplicate_rate": dup, "pattern_diversity": pat_div,
        "dominant_pattern": dom_pat, "dominant_share": dom_share,
        "judge_corr": corr, "leniency_bias": bias,
    }


# ----------------------------------------------------------------------------
# 2. Selection policies (interchangeable; all return subset of candidates)
# ----------------------------------------------------------------------------
def sel_topk(cands: list[dict], hist: list[list[dict]], k: int = K_TARGET) -> list[dict]:
    return sorted(cands, key=lambda a: a["final_score"], reverse=True)[:k]


def sel_thresh90(cands: list[dict], hist: list[list[dict]]) -> list[dict]:
    return sorted([a for a in cands if a["final_score"] >= 90],
                  key=lambda a: a["final_score"], reverse=True)


def sel_floor_caps(cands: list[dict], hist: list[list[dict]],
                   floor: float = FLOOR, cap: int = CAP_PER_PID,
                   kmin: int = MIN_KEPT, k: int = K_TARGET) -> list[dict]:
    pool = sorted([a for a in cands if a["final_score"] >= floor],
                  key=lambda a: a["final_score"], reverse=True)
    kept, per_pid = [], Counter()
    for a in pool:  # respect cap
        if per_pid[a["problem_id"]] < cap:
            kept.append(a)
            per_pid[a["problem_id"]] += 1
        if len(kept) >= k:
            break
    if len(kept) < kmin:  # backfill ignoring cap until minimum size
        for a in sorted(cands, key=lambda a: a["final_score"], reverse=True):
            if a in kept:
                continue
            kept.append(a)
            if len(kept) >= kmin:
                break
    return kept


def _bucket(a: dict) -> tuple:
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def sel_quality_novelty(cands: list[dict], hist: list[list[dict]], k: int = K_TARGET,
                        w_q: float = 0.65, w_n: float = 0.35) -> list[dict]:
    freq = Counter()
    for h in hist[-2:]:  # recent kept history sets the novelty background
        for a in h:
            freq[_bucket(a)] += 1
    mx = max((a["final_score"] for a in cands), default=100) or 100
    picked: list[dict] = []
    remaining = list(cands)
    for _ in range(min(k, len(cands))):
        def score(a: dict) -> float:
            nov = 1.0 / (1.0 + freq[_bucket(a)])
            return w_q * (a["final_score"] / mx) + w_n * nov
        nxt = max(remaining, key=score)
        picked.append(nxt)
        remaining.remove(nxt)
        freq[_bucket(nxt)] += 1  # within-round novelty update (greedy)
    return picked


def sel_coverage_grid(cands: list[dict], hist: list[list[dict]], k: int = K_TARGET) -> list[dict]:
    """MAP-Elites-lite: cell = pid x length-bin; keep cell champions, take top-k
    across champions, guaranteeing >=8 distinct pids when possible."""
    cells: dict[tuple, dict] = {}
    for a in cands:
        nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
        cell = (a["problem_id"], nbin)
        if cell not in cells or a["final_score"] > cells[cell]["final_score"]:
            cells[cell] = a
    champs = sorted(cells.values(), key=lambda a: a["final_score"], reverse=True)
    kept = champs[:k]
    if len({a["problem_id"] for a in kept}) < 8:  # repair coverage
        have = {a["problem_id"] for a in kept}
        for a in sorted(cands, key=lambda a: a["final_score"], reverse=True):
            if a["problem_id"] not in have:
                kept.append(a)
                have.add(a["problem_id"])
            if len(have) >= 8 or len(kept) >= k + 4:
                break
    return kept[:max(k, len(kept))]


POLICIES = {"topk": sel_topk, "thresh90": sel_thresh90, "floor_caps": sel_floor_caps,
            "qual_novelty": sel_quality_novelty, "coverage_grid": sel_coverage_grid}

# ----------------------------------------------------------------------------
# 3. Judge variants
# ----------------------------------------------------------------------------
def _blind_raw(rule_score: float, judge_sm: base.SimulatedModel, rng: random.Random) -> float:
    q = judge_sm.params["self_critique"]
    return max(0, min(100, rule_score + (1 - q) * 4 + rng.gauss(0, (1.05 - q) * 18)))


def _fit_affine(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least-squares ys ~= a*xs + b (for calibrating raw judge -> verifier)."""
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 1.0
    return round(a, 3), round(my - a * mx, 3)


def make_golden_set() -> list[dict]:
    """Small labeled set: 24 arts from SM-0, rule-scored (no judge). Fixed seed."""
    sm0 = base.make_sm0()
    rng = random.Random(999)
    arts = []
    for i, prob in enumerate(base.PROBLEMS * 2):
        arts.append(base.generate_artifact(sm0, prob, f"GOLD-{i:02d}", -1, rng))
    for a in arts:
        a.update(base.rule_evaluate(a))
    return arts


def evaluate_with_judge(arts: list[dict], judge_sm: base.SimulatedModel,
                        kind: str, alpha: float, seed: int,
                        calib: tuple[float, float] | None) -> None:
    rng = random.Random(seed)
    for a in arts:
        r = base.rule_evaluate(a)
        a.update(r)
        raw = _blind_raw(r["rule_score"], judge_sm, rng)
        if kind == "blind":
            j = round(raw, 1)
        elif kind == "verifier_assisted":
            j = round(0.6 * r["rule_score"] + 0.4 * raw, 1)  # judge can call verifier tool
        elif kind == "calibrated":
            ac, bc = calib or (1.0, 0.0)
            j = round(max(0, min(100, ac * raw + bc)), 1)
        else:
            raise ValueError(kind)
        a["judge_version"], a["judge_score"] = judge_sm.version, j
        a["judge_kind"], a["alpha_rule"] = kind, alpha
        a["final_score"] = round(alpha * r["rule_score"] + (1 - alpha) * j, 1)
        a["eval_mix"] = f"{kind} alpha={alpha}"
        a["rationale"] += f" Judge({kind},{judge_sm.version})={j}."


# ----------------------------------------------------------------------------
# 4. Protocol driver: normal -> collapse -> recovery
# ----------------------------------------------------------------------------
PHASE_OF = {0: "normal", 1: "normal", 2: "normal", 3: "collapse",
            4: "collapse", 5: "recovery", 6: "recovery"}
JUDGES = ["blind", "verifier_assisted", "calibrated"]
BASE_SEED = 20260907


def run_combo(policy: str, judge_kind: str, use_gating: bool = False) -> dict:
    """7 rounds per combo. Collapse phase forces topk k=8 + low temp for all
    combos (identical pressure); recovery re-enables policy + re-imports R1,R2."""
    tag = f"{policy}x{judge_kind}{'+gate' if use_gating else ''}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    models = [sm.to_dict()]
    kept_hist: list[list[dict]] = []       # kept sets by global round
    all_kept_flat: list[dict] = []         # for training pools
    rounds_out: list = []
    prev_corr: list = [None]
    lock_streak, prev_dom = 0, None
    golden = make_golden_set()
    # fit calibration once on golden set with the R0 judge (stale-calibration limit noted)
    jrng = random.Random(777)
    raw_g = [_blind_raw(a["rule_score"], sm, jrng) for a in golden]
    calib = _fit_affine(raw_g, [a["rule_score"] for a in golden])

    for g in range(7):
        phase = PHASE_OF[g]
        seed_g, seed_j = BASE_SEED + g * 100, BASE_SEED + g * 7 + 11  # shared across combos
        arts = base.generate_batch(sm, g, NPP, seed_g)
        # judge model = current sm (self-evaluation, evolving); R0 uses rule only
        if g == 0:
            for a in arts:
                a.update(base.rule_evaluate(a))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only R0"})
        else:
            alpha = 0.5
            if use_gating:  # gate on previous round's agreement
                alpha = 0.8 if (prev_corr[-1] is not None and prev_corr[-1] < 0.5) else 0.5
            evaluate_with_judge(arts, sm, judge_kind, alpha, seed_j, calib)
        # selection
        if phase == "collapse":
            kept = sel_topk(arts, kept_hist, k=COLLAPSE_K)
            sel_name = "topk-8 (induced)"
        else:
            kept = POLICIES[policy](arts, kept_hist)
            sel_name = policy
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"] = a["id"] in kid
            a["phase"], a["combo"] = phase, tag
        m = compute_round_metrics(arts, kept)
        # mode-lock persistence (experiment-level collapse signal)
        if m["dominant_share"] > 0.4 and m["dominant_pattern"] == prev_dom:
            lock_streak += 1
        elif m["dominant_share"] > 0.4:
            lock_streak, prev_dom = 1, m["dominant_pattern"]
        else:
            lock_streak, prev_dom = 0, m["dominant_pattern"]
        m["mode_lock_persistence"] = lock_streak
        prev_corr.append(m["judge_corr"])
        # train next SM (except after last round)
        nxt = None
        if g < 6:
            nphase = PHASE_OF[g + 1]
            if nphase == "collapse":
                pool, temp = kept, 0.55  # narrow, recent-only
            elif nphase == "recovery":
                pool = ([a for h in [kept_hist[1], kept_hist[2]] for a in h] + kept
                        if len(kept_hist) >= 3 else kept)  # historical re-import R1+R2
                temp = 0.90
            else:
                pool, temp = kept, 0.85
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [g],
                                     temp_override=temp,
                                     lesson=f"[{phase}->{nphase}|{sel_name}|{judge_kind}] "
                                            f"keep {len(kept)}; cov {m['category_coverage']}.")
            if nphase == "collapse":  # brakes off: diversity decays
                nxt.params["diversity"] = max(0.2, sm.params["diversity"] - 0.10)
            models.append(nxt.to_dict())
        rounds_out.append({"g": g, "phase": phase, "selection": sel_name,
                           "judge": judge_kind, "alpha": arts[0].get("alpha_rule"),
                           "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid),
                           "artifacts": arts})
        kept_hist.append(kept)
        all_kept_flat.extend(kept)
        sm = nxt if nxt else sm
        print(f"{tag} G{g} [{phase}/{sel_name}/{judge_kind}]: "
              f"corr={m['correct_rate']} cov={m['category_coverage']} ent={m['selection_entropy']} "
              f"dup={m['duplicate_rate']} kept={len(kept)} jcorr={m['judge_corr']} bias={m['leniency_bias']}")
    # recovery scoring: restore R1-R2 baseline coverage & quality by G6?
    base_cov = min(rounds_out[1]["metrics"]["category_coverage"],
                   rounds_out[2]["metrics"]["category_coverage"])
    base_q = min(rounds_out[1]["metrics"]["correct_rate"],
                 rounds_out[2]["metrics"]["correct_rate"])
    rec_time, success = None, False
    for i in (5, 6):
        mm = rounds_out[i]["metrics"]
        if mm["category_coverage"] >= base_cov and mm["correct_rate"] >= base_q - 0.05:
            rec_time, success = (i - 4), True  # rounds after collapse end
            break
    return {"combo": tag, "policy": policy, "judge": judge_kind, "gated": use_gating,
            "calibration": {"a": calib[0], "b": calib[1]},
            "baseline_cov": base_cov, "baseline_q": base_q,
            "recovery_time": rec_time, "recovery_success": success,
            "models": models, "rounds": rounds_out}


def main():
    combos = [(p, j, g) for p in ["topk", "thresh90", "floor_caps", "qual_novelty", "coverage_grid"]
              for j, g in [("blind", False), ("verifier_assisted", False), ("calibrated", True)]]
    print(f"Running {len(combos)} combos x 7 rounds...")
    results = [run_combo(p, j, g) for p, j, g in combos]
    # machine-readable JSON (metrics + kept ids + lineage; full CoT kept too)
    with open(OUT / "harness_results.json", "w") as f:
        json.dump({"npp": NPP, "k_target": K_TARGET, "collapse_k": COLLAPSE_K,
                   "combos": results}, f, indent=1)
    # markdown report
    lines = ["# Flywheel harness report — collapse dynamics × evaluator design\n",
             f"Combos: {len(results)} (5 policies × 3 judges), 7 rounds each "
             "(R0-2 normal, R3-4 induced top-8 collapse, R5-6 recovery w/ R1+R2 re-import). "
             "Seeds shared across combos.\n",
             "## Recovery + collapse-depth table (G4 = collapse bottom, G6 = post-recovery)\n",
             "| combo | G2 cov/corr | G4 cov/corr/dup | G6 cov/corr | recovery |",
             "|---|---|---|---|---|"]
    for r in results:
        m2, m4, m6 = r["rounds"][2]["metrics"], r["rounds"][4]["metrics"], r["rounds"][6]["metrics"]
        rec = f"OK in {r['recovery_time']}" if r["recovery_success"] else "FAIL"
        lines.append(f"| {r['combo']} | {m2['category_coverage']}/{m2['correct_rate']} "
                     f"| {m4['category_coverage']}/{m4['correct_rate']}/{m4['duplicate_rate']} "
                     f"| {m6['category_coverage']}/{m6['correct_rate']} | {rec} |")
    # judge-effect summary (avg over policies)
    lines.append("\n## Judge effects (mean over policies)\n")
    for j in ["blind", "verifier_assisted", "calibrated"]:
        sub = [r for r in results if r["judge"] == j]
        g6c = mean(r["rounds"][6]["metrics"]["correct_rate"] for r in sub)
        g6v = mean(r["rounds"][6]["metrics"]["category_coverage"] for r in sub)
        br = mean([r["rounds"][4]["metrics"]["leniency_bias"] for r in sub
                   if r["rounds"][4]["metrics"]["leniency_bias"] is not None] or [0])
        lines.append(f"- {j}: G6 corr {g6c:.3f}, G6 cov {g6v:.3f}, collapse-phase bias {br:.1f}.")
    lines.append("\n## Takeaways\n"
                 "- See final chat summary for the interpreted takeaways.\n")
    (OUT / "harness_report.md").write_text("\n".join(lines) + "\n")
    print("Wrote harness_results.json + harness_report.md")


if __name__ == "__main__":
    main()

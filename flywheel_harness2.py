"""
Flywheel harness v2 — follow-up fixes + harder stress tests
============================================================
Fixes three v1 issues, adds two stress conditions, hardens recovery analysis.

FIX 1 — mode-lock redefinition (v1 dominant_share maxed at ~0.06, always 0):
  New: per-category phrasing-template lock. Each CoT step is classified into
  a template id (0..4 from base.STEP_PHRASES, or 5 = distractor/unknown).
  mode_lock_strength = max over pids of (dominant-template share within pid).
  mode_lock_persistence = consecutive rounds where the SAME (pid, template)
  dominates with share > 0.6. Nonzero only on genuine local homogenization.

FIX 2 — gating trigger retuned (v1 corr<0.5 never fired; corr saturates ~0.97):
  New trigger: alpha=0.8 if prev corr < 0.97 OR |prev bias| > 1.5, else 0.5.
  Rationale: in a bimodal-score regime Pearson saturates, so the bias term
  carries the signal (stale calibration shows as bias, not decorrelation).

FIX 3 — per-round recalibration (v1 fit-once went stale: bias ~-3 forever):
  New: refit affine golden mapping EVERY round with the current judge SM.
  (Golden rule scores fixed; golden raw scores recomputed with current judge.)

NEW STRESS A — pure SM-judge (alpha=0): final_score = judge only. Tests
  whether ranking survives without any verifier anchor.

NEW STRESS B — gradual collapse ramp: G3/G4/G5 kept k = 14/10/6 with temps
  0.8/0.65/0.55 (vs v1 sharp 8/8). 8 rounds total: G0-2 normal, G3-5 ramp,
  G6-7 recovery.

RECOVERY — margin-to-baseline + import comparison:
  Margins (not binary): cov_margin = G7 cov - baseline_cov;
  q_margin = G7 corr - (baseline_q - 0.05). Positive = restored.
  Import modes (pool capped at 36 for fairness):
    simple  = most-recent 36 from {R1,R2,last} by final_score;
    utility = top 36 from ALL history+last by
              U = final/100 + 0.5*(pid currently forgotten) + 0.25*novelty,
              novelty = 1/(1+bucket count). Directly tests whether targeting
              forgotten categories beats recency.

Run:  python flywheel_harness2.py
Out:  harness2_results.json, harness2_report.md
Stdlib only. Seeds shared across combos (BASE_SEED + g offsets).
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
import flywheel_sim as base
import flywheel_harness as h1  # reuse POLICIES, _blind_raw, _fit_affine, make_golden_set

OUT = Path(__file__).parent
NPP = 3
N_CATS = len(base.PROBLEMS)
BASE_SEED = 20260907
RAMP_KS = {3: 14, 4: 10, 5: 6}
RAMP_TEMPS = {3: 0.80, 4: 0.65, 5: 0.55}
POOL_CAP = 36

# ----------------------------------------------------------------------------
# FIX 1: template-id classification + per-category mode lock
# ----------------------------------------------------------------------------
_TMPL_PREFIX = ["compute:", "next,", "so ", "check:", "then "]  # lowercased starts


def template_id(step: str) -> int:
    s = step.strip().lower()
    for i, p in enumerate(_TMPL_PREFIX):
        if s.startswith(p):
            return i
    return 5  # distractor / unknown


def mode_lock_info(arts: list[dict]) -> dict:
    """Max over pids of dominant-template share + which (pid,tmpl) it is."""
    by_pid: dict[str, list[int]] = {}
    for a in arts:
        by_pid.setdefault(a["problem_id"], []).extend(template_id(s) for s in a["cot"])
    best = {"pid": None, "tmpl": None, "share": 0.0}
    for pid, tids in by_pid.items():
        c = Counter(tids)
        t, n = c.most_common(1)[0]
        share = round(n / len(tids), 3)
        if share > best["share"]:
            best = {"pid": pid, "tmpl": t, "share": share}
    return best


# ----------------------------------------------------------------------------
# Metrics v2 (extends v1 suite; keeps all v1 fields for comparability)
# ----------------------------------------------------------------------------
def compute_metrics_v2(arts: list[dict], kept: list[dict]) -> dict:
    m = h1.compute_round_metrics(arts, kept)  # v1 fields incl. old mode_lock (ignored)
    lock = mode_lock_info(arts)
    m["mode_lock_strength"] = lock["share"]
    m["mode_lock_where"] = [lock["pid"], lock["tmpl"]]
    m.pop("mode_lock_persistence", None)  # experiment-level; set by driver
    return m


# ----------------------------------------------------------------------------
# Judge evaluation v2 (per-round calib, pure alpha=0 support)
# ----------------------------------------------------------------------------
def evaluate_v2(arts, judge_sm, kind, alpha, seed, calib):
    rng = random.Random(seed)
    for a in arts:
        r = base.rule_evaluate(a)
        a.update(r)
        raw = h1._blind_raw(r["rule_score"], judge_sm, rng)
        if kind == "blind":
            j = round(raw, 1)
        elif kind == "verifier_assisted":
            j = round(0.6 * r["rule_score"] + 0.4 * raw, 1)
        elif kind == "calibrated":
            ac, bc = calib
            j = round(max(0, min(100, ac * raw + bc)), 1)
        a["judge_version"], a["judge_score"] = judge_sm.version, j
        a["judge_kind"], a["alpha_rule"] = kind, alpha
        a["final_score"] = round(alpha * r["rule_score"] + (1 - alpha) * j, 1)
        a["eval_mix"] = f"{kind} alpha={alpha}"
        a["rationale"] += f" Judge({kind},{judge_sm.version})={j}."


def fit_calib_for(judge_sm) -> tuple[float, float]:
    golden = make_golden_once()
    jrng = random.Random(777)
    raw = [h1._blind_raw(a["rule_score"], judge_sm, jrng) for a in golden]
    return h1._fit_affine(raw, [a["rule_score"] for a in golden])


_GOLDEN = None


def make_golden_once():
    global _GOLDEN
    if _GOLDEN is None:
        _GOLDEN = h1.make_golden_set()
    return _GOLDEN


# ----------------------------------------------------------------------------
# Recovery pools: simple vs utility-weighted (both capped at POOL_CAP)
# ----------------------------------------------------------------------------
def _bucket(a):
    nbin = 1 if len(a["cot"]) == 1 else (2 if len(a["cot"]) == 2 else 3)
    return (a["problem_id"], a["correct"], nbin)


def simple_pool(kept_hist, g) -> list[dict]:
    cand = [a for h in (kept_hist[1:3] + [kept_hist[g - 1]]) for a in h]
    cand = sorted(cand, key=lambda a: a["final_score"], reverse=True)
    return cand[:POOL_CAP]


def utility_pool(kept_hist, g) -> list[dict]:
    last = kept_hist[g - 1]
    forgotten = set(h1.compute_round_metrics(last, last)["category_forgetting"])
    freq = Counter(_bucket(a) for h in kept_hist for a in h)
    cand = [a for h in kept_hist for a in h]
    scored = sorted(
        cand,
        key=lambda a: (a["final_score"] / 100.0
                       + 0.5 * (a["problem_id"] in forgotten)
                       + 0.25 * (1.0 / (1.0 + freq[_bucket(a)]))),
        reverse=True,
    )
    # de-dup by id, keep last-round items preferred on ties (stable: last first)
    seen, out = set(), []
    for a in sorted(scored, key=lambda a: a["id"] not in {x["id"] for x in last}):
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
        if len(out) >= POOL_CAP:
            break
    return out


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
PHASE_OF = {0: "normal", 1: "normal", 2: "normal", 3: "collapse",
            4: "collapse", 5: "collapse", 6: "recovery", 7: "recovery"}


def run_combo(policy: str, judge_kind: str, alpha_mode: str, import_mode: str) -> dict:
    """alpha_mode: fixed05 | gated097 | pure0. import_mode: simple | utility."""
    tag = f"{policy}x{judge_kind}x{alpha_mode}x{import_mode}"
    sm = base.make_sm0()
    sm.version = f"{tag}-G0"
    kept_hist: list = []
    rounds_out: list = []
    prev_corr, prev_bias = None, None
    lock_key, lock_streak = None, 0
    calib = fit_calib_for(sm)
    calibs = [calib]

    for g in range(8):
        phase = PHASE_OF[g]
        arts = base.generate_batch(sm, g, NPP, BASE_SEED + g * 100)
        if g == 0:
            for a in arts:
                a.update(base.rule_evaluate(a))
                a.update({"judge_version": None, "judge_score": None,
                          "final_score": a["rule_score"], "eval_mix": "rule-only R0",
                          "judge_kind": None, "alpha_rule": None})
        else:
            if judge_kind == "calibrated":
                calib = fit_calib_for(sm)  # FIX 3: refit every round
                calibs.append(calib)
            if alpha_mode == "pure0":
                alpha = 0.0
            elif alpha_mode == "gated097":  # FIX 2: retuned trigger
                alpha = 0.8 if (prev_corr is not None and
                                (prev_corr < 0.97 or abs(prev_bias or 0) > 1.5)) else 0.5
            else:
                alpha = 0.5
            evaluate_v2(arts, sm, judge_kind, alpha, BASE_SEED + g * 7 + 11, calib)
        # selection
        if phase == "collapse":
            kept = h1.sel_topk(arts, kept_hist, k=RAMP_KS[g])
            sel_name = f"topk-{RAMP_KS[g]} (ramp)"
        else:
            kept = h1.POLICIES[policy](arts, kept_hist)
            sel_name = policy + ("+util-import" if phase == "recovery" and import_mode == "utility" else "")
        kid = {a["id"] for a in kept}
        for a in arts:
            a["kept"] = a["id"] in kid
            a["phase"], a["combo"] = phase, tag
        m = compute_metrics_v2(arts, kept)
        # FIX 1: persistence on stable (pid,tmpl) lock with share>0.6
        key = (m["mode_lock_where"][0], m["mode_lock_where"][1])
        if m["mode_lock_strength"] > 0.6 and key == lock_key:
            lock_streak += 1
        elif m["mode_lock_strength"] > 0.6:
            lock_key, lock_streak = key, 1
        else:
            lock_key, lock_streak = key, 0
        m["mode_lock_persistence"] = lock_streak
        prev_corr, prev_bias = m["judge_corr"], m["leniency_bias"]
        # train next
        nxt = None
        if g < 7:
            nphase = PHASE_OF[g + 1]
            if nphase == "collapse":
                pool, temp = kept, RAMP_TEMPS[g + 1]
            elif nphase == "recovery":
                pool = simple_pool(kept_hist + [kept], g + 1) if import_mode == "simple" \
                    else utility_pool(kept_hist + [kept], g + 1)
                temp = 0.90
            else:
                pool, temp = kept, 0.85
            nxt = base.train_next_sm(f"{tag}-G{g+1}", [sm], pool, [g],
                                     temp_override=temp,
                                     lesson=f"[{phase}->{nphase}|{sel_name}|{judge_kind}/{alpha_mode}] keep {len(kept)}.")
            if nphase == "collapse":
                nxt.params["diversity"] = max(0.2, sm.params["diversity"] - 0.10)
            sm_next = nxt
        else:
            sm_next = sm
        rounds_out.append({"g": g, "phase": phase, "selection": sel_name,
                           "alpha": arts[0].get("alpha_rule"), "calib": calib,
                           "metrics": m, "model": sm.to_dict(),
                           "kept_ids": sorted(kid), "artifacts": arts})
        kept_hist.append(kept)
        sm = sm_next
        print(f"{tag} G{g} [{phase}/{sel_name} a={arts[0].get('alpha_rule')}]: "
              f"corr={m['correct_rate']} cov={m['category_coverage']} ent={m['selection_entropy']} "
              f"lock={m['mode_lock_strength']}{m['mode_lock_where']}+{lock_streak} "
              f"jcorr={m['judge_corr']} bias={m['leniency_bias']} calib={calib}")
    # margins (not binary)
    base_cov = min(rounds_out[1]["metrics"]["category_coverage"],
                   rounds_out[2]["metrics"]["category_coverage"])
    base_q = min(rounds_out[1]["metrics"]["correct_rate"],
                 rounds_out[2]["metrics"]["correct_rate"])
    fin = rounds_out[7]["metrics"]
    cov_margin = round(fin["category_coverage"] - base_cov, 3)
    q_margin = round(fin["correct_rate"] - (base_q - 0.05), 3)
    # recovery time: first G6/G7 round with both margins >= 0
    rec_time = None
    for i in (6, 7):
        mm = rounds_out[i]["metrics"]
        if mm["category_coverage"] - base_cov >= 0 and mm["correct_rate"] - (base_q - 0.05) >= 0:
            rec_time = i - 5
            break
    return {"combo": tag, "policy": policy, "judge": judge_kind,
            "alpha_mode": alpha_mode, "import_mode": import_mode,
            "baseline_cov": base_cov, "baseline_q": base_q,
            "cov_margin": cov_margin, "q_margin": q_margin,
            "recovery_time": rec_time, "recovery_success": rec_time is not None,
            "rounds": rounds_out}


def main():
    combos = []
    for p in ["topk", "floor_caps", "coverage_grid"]:
        combos.append((p, "blind", "fixed05", "simple"))
        combos.append((p, "verifier_assisted", "fixed05", "simple"))
        combos.append((p, "blind", "gated097", "simple"))          # calibrated+gated below
        combos.append((p, "calibrated", "gated097", "simple"))     # FIX 2+3 combined
        combos.append((p, "blind", "pure0", "simple"))             # STRESS A
    # import-mode head-to-head on two representative combos (STRESS recovery)
    combos.append(("floor_caps", "blind", "fixed05", "utility"))
    combos.append(("coverage_grid", "blind", "fixed05", "utility"))
    print(f"Running {len(combos)} combos x 8 rounds (gradual ramp)...")
    results = [run_combo(*c) for c in combos]
    with open(OUT / "harness2_results.json", "w") as f:
        json.dump({"combos": results}, f, indent=1)
    # report
    L = ["# Harness v2 report — fixes + pure-judge + ramp + import comparison\n",
         "8 rounds: G0-2 normal, G3-5 gradual collapse (top-14/10/6), G6-7 recovery.\n",
         "## Per-combo margins (G7 vs baseline)",
         "| combo | G2 cov/corr | G5 cov/corr | G7 cov/corr | cov_margin | q_margin | rec_time |",
         "|---|---|---|---|---|---|---|"]
    for r in results:
        m2, m5, m7 = r["rounds"][2]["metrics"], r["rounds"][5]["metrics"], r["rounds"][7]["metrics"]
        L.append(f"| {r['combo']} | {m2['category_coverage']}/{m2['correct_rate']} "
                 f"| {m5['category_coverage']}/{m5['correct_rate']} "
                 f"| {m7['category_coverage']}/{m7['correct_rate']} "
                 f"| {r['cov_margin']:+.3f} | {r['q_margin']:+.3f} | {r['recovery_time']} |")
    (OUT / "harness2_report.md").write_text("\n".join(L) + "\n")
    print("Wrote harness2_results.json + harness2_report.md")


if __name__ == "__main__":
    main()

"""
Package 28 — Heterogeneous-ecosystem sim (WQ4 build, spec `wq4_spec.md` FROZEN)
=================================================================================
Tiers as capability profiles (all generative), specialist diets, union pooling:
  cheap    tier_acc [0.90,0.60,0.35] diet {0,1}  breadth volume
  mid      tier_acc [0.70,0.90,0.50] diet {1}    narrow-deep correctness
  frontier tier_acc [0.95,0.90,0.75] diet {2}    deep-narrow specialty, FROZEN
Frontier = seed + critique: scarce golden generations to pool + re-judge triggered
by Mid×rule disagreement (|mid_judge - rule| > 25, escalation counted = WQ3 data).
Mid pool-construction AND selection instrumented separately. Bank EXCLUDED from all
pools (channel annotation trivially clean). No poison (ecosystem question, clean).
Matched total generation budget N=144 calls/round/arm:
  eco = 102 cheap + 30 mid + 12 frontier; solos = 144 own-tier;
  CM = 108+36; CF = 132+12; MF = 132+12.
Phase 1 (G0-G2): diet specialization self-loops, screened-quota pools, blind judges
  (cheap stream Mid-judged from the start). Phase 2 arms G3-G6 (4 rounds):
  solo×3, pair×3, ecosystem, consult (Mid parent + union pool), graft-ceiling
  (per-slice max tier_acc across solo children + union pool; labeled ceiling).
  Ecosystem = THREE specialist lines (cheap/mid/frontier children on stream-specific
  pools), endpoint JOINT per-slice max — structurally distinct from consult
  (one mid line on the union pool). v1 trained one mid line for both (identical);
  disambiguated as a spec defect (core comparison would be vacuous otherwise).
Endpoints: probe-hard PRIMARY (fresh probe/round), NOVEL/KNOWN co-primary (final
batch split by correct-pool-membership), coverage (distinct known pids), taxonomy
classes (eco child vs solo children) + joint tiers>=HIGH count, Wilson-gated formal
gate C_eco > max(C_solos, C_consult) on probe-hard (graft excluded from gate).
Stage-1a precursor (same file): hand pair cheap+frontier, no router, union pool,
2 rounds × 3 seeds — pass = joint sustain (t0>=0.60 and t2>=0.60). Silent → ecosystem
runs Pareto-framing only. Stage-1b: compositional R1 tasks unrepresentable in current
bank (no skill interaction in correctness draws) — reported, not coded.

Usage: python flywheel_pkg28.py (3 seeds)
Out: pkg28_eco.json
"""
from __future__ import annotations
import copy
import json
import random
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import flywheel_sim as base
import flywheel_harness as h1
import flywheel_harness4 as h4
import flywheel_pkg9 as p9
import capability_ledger as cl

OUT = Path(__file__).parent
BASE_SEED = 20260907
SEEDS = [0, 1500, 3000]
NPP = 3
N_TOTAL = 144
SPLITS = {"cheap": 102, "mid": 30, "frontier": 12}
# --per-slice: DIAGNOSTIC matching (round5-ii). Every stream gets N_TOTAL calls
# (eco total 432 vs solo 144): isolates per-slice capability from budget shape.
# Default (total-cost) matching is the external-facing frame; per-slice answers
# whether "specialist wins on-slice" survives equal exposure. Output switches to
# pkg28b_perslice.json. Phase-1 specialization identical in both modes.
PER_SLICEMATCH = "--per-slice" in sys.argv
DIETS = {"cheap": {0, 1}, "mid": {1}, "frontier": {2}}
TIERACC = {"cheap": [0.90, 0.60, 0.35], "mid": [0.70, 0.90, 0.50],
           "frontier": [0.95, 0.90, 0.75]}
KEEP_Q = 6  # kept per allowed tier per stream
POOL_Q = 12  # screened quota per allowed tier
ESC_TRIG = 25  # |mid_judge - rule| trigger for frontier escalation


def tier_corr(arts):
    out = {}
    for t in (0, 1, 2):
        sub = [a for a in arts if a["tier"] == t]
        out[str(t)] = round(mean(1.0 if a["correct"] else 0.0 for a in sub), 3) if sub else None
    return out


def make_tier(name, tag):
    sm = base.make_sm0()
    sm.params.update({"tier_acc": list(TIERACC[name]), "arithmetic_acc": 0.70,
                      "reason_depth": 2.2 if name != "cheap" else 1.6,
                      "format_rel": 0.95, "temperature": 0.85, "diversity": 0.7,
                      "self_critique": {"cheap": 0.5, "mid": 0.8, "frontier": 0.9}[name],
                      "misc_rate": 0.0})
    sm.version = f"{tag}-{name}"
    return sm


def gen_stream(sm, n_probs, rnd, seed, prefix, bank, tiers=None):
    # Specialist data sourcing: streams sample their diet tiers (so a scarce
    # stream always carries in-domain problems; correctness stays stochastic).
    pool = [p for p in bank if p["tier"] in tiers] if tiers else list(bank)
    rng = random.Random(seed)
    # with replacement: diet pools can be smaller than the call budget
    probs = [pool[rng.randrange(len(pool))] for _ in range(n_probs)]
    arts, k = [], 0
    for prob in probs:
        for _ in range(NPP):
            k += 1
            a = base.generate_artifact(sm, prob, f"{prefix}-{k:03d}", rnd, rng)
            a["tier"] = prob["tier"]  # gen_batch stamps this; generate_artifact does not
            arts.append(a)
    return arts


def judge_stream(arts, gen_sm, judge_sm, kind, alpha, js):
    h4.evaluate_v4(arts, judge_sm, kind, alpha, js, (1.0, 0.0), "v4")
    for a in arts:
        a["_gen"] = gen_sm.version


def quota_keep(arts, diet):
    kept = []
    for t in sorted(diet):
        kept.extend(sorted([a for a in arts if a["tier"] == t],
                           key=lambda a: a["final_score"], reverse=True)[:KEEP_Q])
    return kept


def screened_pool(kept_hist, diet):
    src = [a for h in kept_hist[-3:] for a in h]
    cand = [a for a in src if a["rule_score"] >= 85 and not a.get("_misc")]
    out = []
    for t in sorted(diet):
        out.extend(sorted([a for a in cand if a.get("tier") == t],
                          key=lambda a: a["final_score"], reverse=True)[:POOL_Q])
    return out


def probe_all(sm, seed, g):
    probe = p9.gen_batch(sm, p9.PROBE_BANK, g, 2, BASE_SEED + seed + 9000 + g * 100,
                         f"PRB{g}-")
    for a in probe:
        a.update(h4.rule_evaluate_v4(a, "v4"))
        a["final_score"] = a["rule_score"]
    tc = tier_corr(probe)
    n2 = sum(1 for a in probe if a["tier"] == 2)
    return tc, n2


def run_stream_set(tiers, sms, judges, g, seed, tag, probs_split):
    """Generate+judge+keep one round for a set of tier streams. Returns kept per tier."""
    kept = {}
    off = {"cheap": 0, "mid": 11, "frontier": 23, "consult": 5, "graft": 7}
    for tr in tiers:
        gs = BASE_SEED + seed + g * 100 + off.get(tr, 0)
        js = BASE_SEED + seed + g * 7 + 11 + off.get(tr, 0)
        arts = gen_stream(sms[tr], probs_split[tr] // NPP, g, gs, f"R{g}-{tr}-", p9.BANK,
                          DIETS[tr])
        judge_stream(arts, sms[tr], judges[tr], "blind", 0.5, js)
        k = quota_keep(arts, DIETS[tr])
        kid = {a["id"] for a in k}
        for a in arts:
            a["kept"], a["phase"], a["combo"] = a["id"] in kid, "eco", tag
        kept[tr] = (arts, k)
    return kept


def escalate(arts, frontier_sm, seed):
    """Frontier re-judge where Mid×rule disagree. Returns escalation count."""
    n = 0
    for a in arts:
        if abs(a.get("judge_score", 0) - a.get("rule_score", 0)) > ESC_TRIG:
            n += 1
            h4.evaluate_v4([a], frontier_sm, "blind", 0.5, seed + n, (1.0, 0.0), "v4")
            a["escalated"] = True
    return n


def scale_split(members):
    """Split N_TOTAL across member tiers proportional to SPLITS weights."""
    if PER_SLICEMATCH:
        return {t: N_TOTAL for t in members}
    w = {t: SPLITS[t] for t in members}
    tot = sum(w.values())
    out, acc = {}, 0
    for i, t in enumerate(members):
        q = N_TOTAL * w[t] // tot
        out[t] = q
        acc += q
    out[members[0]] += N_TOTAL - acc
    return out


def run_seed(seed):
    tag = f"ecoxseed{seed}"
    sms = {t: make_tier(t, tag) for t in ("cheap", "mid", "frontier")}
    # Phase 1: specialization G0-G2 (frontier stream uses frozen SM; children separate)
    hist = {t: [] for t in sms}
    kids = {t: sms[t] for t in sms}  # current child per tier (frontier child trains too)
    prev = {}
    for g in range(3):
        judges = {"cheap": kids["mid"], "mid": kids["mid"], "frontier": sms["frontier"]}
        # NOTE g<... : mid child judges cheap stream (cross-tier judging from round 0)
        kept = run_stream_set(("cheap", "mid", "frontier"), kids, judges, g, seed, tag,
                              {"cheap": 102, "mid": 30, "frontier": 12})
        for t in hist:
            arts, k = kept[t]
            m = h1.compute_round_metrics(arts, k)
            m["tier_corr"] = tier_corr(arts)
            hist[t].append(k)
            pool = screened_pool(hist[t], DIETS[t])
            nxt = base.train_next_sm(f"{tag}-{t}-G{g+1}", [kids[t]], pool,
                                     sorted({a["round"] for a in pool}),
                                     temp_override=0.85, lesson=f"[eco-spec|{t}]")
            if t != "frontier":
                kids[t] = nxt
            # frontier generator stays FROZEN; its child trains (solo-frontier line)
            if t == "frontier":
                kids["frontier_child"] = nxt if g == 0 else base.train_next_sm(
                    f"{tag}-frontier_child-G{g+1}", [kids["frontier_child"]], pool,
                    sorted({a["round"] for a in pool}), temp_override=0.85,
                    lesson="[eco-spec|frontier_child]")
    # fork states per arm family
    arms_def = {"solo-cheap": ("cheap",), "solo-mid": ("mid",), "solo-frontier": ("frontier",),
                "pair-CM": ("cheap", "mid"), "pair-CF": ("cheap", "frontier"),
                "pair-MF": ("mid", "frontier"),
                "ecosystem": ("cheap", "mid", "frontier"),
                "consult": ("consult",), "graft": ("graft",)}
    out = []
    for arm, members in arms_def.items():
        atag = f"{arm}xseed{seed}"
        st = copy.deepcopy({t: {"sm": kids[t], "hist": [list(h) for h in hist[t]]}
                            for t in ("cheap", "mid", "frontier")})
        if "frontier_child" in kids:
            st["frontier_child"] = {"sm": copy.deepcopy(kids["frontier_child"]),
                                    "hist": [list(h) for h in hist["frontier"]]}
        # arm parent model + diet
        if arm.startswith("solo-"):
            t = members[0]
            sm = st[t]["sm"] if t != "frontier" else st["frontier_child"]["sm"]
            diet = set(DIETS[t])
        elif arm == "consult":
            sm = st["mid"]["sm"]
            diet = {0, 1, 2}
        elif arm == "graft":
            sm = copy.deepcopy(st["mid"]["sm"])
            mx = [max(st["cheap"]["sm"].params["tier_acc"][i],
                      st["mid"]["sm"].params["tier_acc"][i],
                      st["frontier_child"]["sm"].params["tier_acc"][i]) for i in range(3)]
            sm.params["tier_acc"] = [round(v, 3) for v in mx]
            sm.version = f"{atag}-graftG3"
            diet = {0, 1, 2}
        else:
            # ecosystem: THREE specialist lines (cheap/mid/frontier children) each
            # training on its own stream pool; endpoint = JOINT per-slice max.
            # (v1 trained one mid line on the union pool = consult duplicate.)
            lines = {"cheap": st["cheap"]["sm"], "mid": st["mid"]["sm"],
                     "frontier": st["frontier_child"]["sm"]}
            line_hist = {t: [list(h) for h in st[t]["hist"]] for t in lines}
            diet = set().union(*(DIETS[t] for t in members))
        arm_hist = []
        for t in (members if arm not in ("consult", "graft") else ("cheap", "mid", "frontier")):
            arm_hist.extend([list(h) for h in st[t]["hist"]])
        if arm in ("consult", "graft"):
            arm_hist = [list(h) for h in st["cheap"]["hist"]] + \
                       [list(h) for h in st["mid"]["hist"]] + \
                       [list(h) for h in st["frontier"]["hist"]]
        rounds, pc = [], None
        esc_tot, margins = 0, []
        for g in range(3, 7):
            if arm in ("consult", "graft"):
                members_g, split = ("cheap", "mid", "frontier"), \
                    ({"cheap": 102, "mid": 30, "frontier": 12} if not PER_SLICEMATCH
                     else {"cheap": 144, "mid": 144, "frontier": 144})
                sms_g = {"cheap": st["cheap"]["sm"], "mid": st["mid"]["sm"],
                         "frontier": sms["frontier"]}
            elif arm.startswith("solo-"):
                t = members[0]
                members_g = (t,)
                sms_g = {t: (st[t]["sm"] if t != "frontier" else sms["frontier"])}
                split = {t: N_TOTAL}
            else:
                members_g = members
                sms_g = {t: (st[t]["sm"] if t != "frontier" else sms["frontier"])
                         for t in members}
                split = scale_split(list(members))
            judges = {t: (st["mid"]["sm"] if t == "cheap" else
                          (sms["frontier"] if t == "frontier" else st["mid"]["sm"]))
                      for t in members_g}
            kept = run_stream_set(members_g, sms_g, judges, g, seed, atag, split)
            arts_all, kept_all = [], []
            for t in members_g:
                arts, k = kept[t]
                arts_all.extend(arts)
                kept_all.extend(k)
                arm_hist.append(k)
            # disagreement-triggered frontier escalation (eco + frontier-bearing pairs)
            if "frontier" in members_g and arm not in ("solo-frontier",):
                e = escalate(arts_all, sms["frontier"], BASE_SEED + seed + g)
                esc_tot += e
            margins.append(round(mean([abs(a.get("judge_score", 0) - a.get("rule_score", 0))
                                       for a in arts_all]), 2))
            kid = {a["id"] for a in kept_all}
            m = h1.compute_round_metrics(arts_all, kept_all)
            m["tier_corr"] = tier_corr(arts_all)
            if arm == "ecosystem":
                # joint measured on PRE-training lines (same timing as solo arms'
                # pre-training models); lines train afterwards.
                line_m = {}
                for t in members:
                    arts_t, k_t = kept[t]
                    line_hist[t].append(k_t)
                    pool_t = screened_pool(line_hist[t], DIETS[t])
                    tc_t, _ = probe_all(lines[t], seed, g)
                    line_m[t] = {"tier_corr": tier_corr(arts_t), "probe": tc_t,
                                 "pool_hard": sum(1 for a in pool_t if a.get("tier") == 2),
                                 "tier_acc": list(lines[t].params["tier_acc"])}
                m["tier_acc"] = [round(max(line_m[t]["tier_acc"][i]
                                           for t in members), 3) for i in range(3)]
                m["probe_tier_corr"] = {str(i): max(line_m[t]["probe"][str(i)] or 0
                                                   for t in members) for i in range(3)}
                m["probe_n2"] = 16
                m["lines"] = line_m
                pool = screened_pool(arm_hist, diet)
                for t in members:
                    pool_t = screened_pool(line_hist[t], DIETS[t])
                    lines[t] = base.train_next_sm(
                        f"{atag}-{t}-G{g+1}", [lines[t]], pool_t,
                        sorted({a["round"] for a in pool_t}),
                        temp_override=0.85, lesson=f"[eco|{t}]")
            else:
                m["tier_acc"] = list(sm.params["tier_acc"])
                pool = screened_pool(arm_hist, diet)
            hk = [a for a in pool if a.get("tier") == 2]
            m["pool_hard"] = len(hk)
            m["pool_tier_fill"] = {str(t): sum(1 for a in pool if a.get("tier") == t)
                                   for t in (0, 1, 2)}
            if arm != "ecosystem":
                tc, n2 = probe_all(sm, seed, g)
                m["probe_tier_corr"] = tc
                m["probe_n2"] = n2
                nxt = base.train_next_sm(f"{atag}-G{g+1}", [sm], pool,
                                         sorted({a["round"] for a in pool}),
                                         temp_override=0.85, lesson=f"[eco|{arm}]")
                sm = nxt
            rounds.append({"g": g, "arm": arm, "metrics": m, "model": sm.to_dict()
                           if arm != "ecosystem" else {t: lines[t].to_dict() for t in members},
                           "kept_ids": sorted(kid), "artifacts": arts_all})
            print(f"{atag} G{g}: tiers={m['tier_corr']} phard={m['probe_tier_corr']['2']} "
                  f"esc={esc_tot}", flush=True)
        # NOVEL/KNOWN split on final batch by correct-pool membership
        cov = set()
        for i in range(len(arm_hist)):
            pool = screened_pool(arm_hist[max(0, i - 2):i + 1], diet)
            for a in pool:
                if a["correct"]:
                    cov.add(a["problem_id"])
        fin_arts = rounds[-1]["artifacts"]
        kn = [a["correct"] for a in fin_arts if a["problem_id"] in cov]
        nv = [a["correct"] for a in fin_arts if a["problem_id"] not in cov]
        novel = {"n_known": len(kn), "n_novel": len(nv),
                 "acc_known": round(mean(kn), 3) if kn else None,
                 "acc_novel": round(mean(nv), 3) if nv else None,
                 "coverage": len(cov)}
        out.append({"combo": atag, "arm": arm, "seed": seed, "diet": sorted(diet),
                    "esc_total": esc_tot, "margins": margins, "novel": novel,
                    "rounds": rounds})
    return {"combos": out}


def stage1a(seed):
    """Hand pair cheap+frontier, no router, union pool. Pass = joint sustain."""
    tag = f"s1axseed{seed}"
    sms = {t: make_tier(t, tag) for t in ("cheap", "frontier")}
    hist = []
    sm_c, sm_f = sms["cheap"], sms["frontier"]
    for g in range(2):
        gs = BASE_SEED + seed + g * 100
        ac = gen_stream(sm_c, 132 // NPP, g, gs, f"S1c{seed}-", p9.BANK, {0, 1})
        h4.evaluate_v4(ac, sm_c, "blind", 0.5, gs + 1, (1.0, 0.0), "v4")
        af = gen_stream(sm_f, 12 // NPP, g, gs + 5, f"S1f{seed}-", p9.BANK, {2})
        h4.evaluate_v4(af, sm_f, "blind", 0.5, gs + 6, (1.0, 0.0), "v4")
        kc = quota_keep(ac, {0, 1})
        kf = quota_keep(af, {2})
        hist.extend([kc, kf])
        pool = screened_pool(hist, {0, 1, 2})
        sm_c = base.train_next_sm(f"{tag}-G{g+1}", [sm_c], pool, [g],
                                  temp_override=0.85, lesson="[s1a]")
    acc = sm_c.params["tier_acc"]
    ok = acc[0] >= 0.60 and acc[2] >= 0.60
    print(f"{tag}: joint t0={acc[0]} t2={acc[2]} -> {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def main():
    s1 = [stage1a(s) for s in SEEDS]
    print(f"STAGE1A: {sum(s1)}/{len(s1)} joint-sustain")
    all_out = []
    for seed in SEEDS:
        all_out.extend(run_seed(seed)["combos"])
    with open(OUT / ("pkg28b_perslice.json" if PER_SLICEMATCH else "pkg28_eco.json"), "w") as f:
        json.dump({"block": "eco-perslice" if PER_SLICEMATCH else "eco",
                   "per_slicematch": PER_SLICEMATCH,
                   "stage1a": s1, "combos": all_out}, f, indent=1)
    print("Wrote", "pkg28b_perslice.json" if PER_SLICEMATCH else "pkg28_eco.json")


if __name__ == "__main__":
    main()

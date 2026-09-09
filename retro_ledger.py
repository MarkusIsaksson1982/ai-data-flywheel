"""
retro_ledger — pkg19-style retro-analysis, zero new simulation compute
============================================================================
Reads already-logged flywheel JSONs (any file with {"combos": [...]}, each
combo with "rounds": [...]) and rebuilds (C, M) + NDS + dormant census +
aggregate-understatement per combo, then aggregates across the corpus.

Usage (standalone or drop-in):
  python retro_ledger.py --logs ../ai-data-flywheel --out ./refs --mode tier
  python retro_ledger.py --logs . --pattern "pkg*.json" --out ./refs

Inputs:  pkg10_tierskills.json, pkg11_recover.json, pkg12_*.json,
         pkg14/15, pkg17_wide.json, harness*.json — any subset works.
         Missing files are skipped; runs without tier info ledger as
         single-slice "overall" (legacy harness regime).

Outputs (all deterministic, sorted keys):
  refs/retro_ledger.json  — per-combo ledgers (C/M/frontier/NDS)
  refs/retro_report.md    — human-readable census (NDS distribution,
                           dormant-frontier table, understatement cases)

Conventions match the repo: stdlib-only, seeded I/O-free of randomness,
console prints PASS/FAIL-style summary lines.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
import capability_ledger as cl


def load_combos(path: Path) -> list:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"SKIP {path.name}: unreadable ({e})")
        return []
    if isinstance(d, dict) and "combos" in d:
        combos = d["combos"]
    elif isinstance(d, list):
        combos = d
    else:
        print(f"SKIP {path.name}: no combos list")
        return []
    out = []
    for c in combos:
        rounds = c.get("rounds", [])
        if len(rounds) >= 2:
            out.append(c)
    print(f"LOAD {path.name}: {len(out)} runs")
    return [(path.name, c) for c in out]


def combo_id(fname: str, c: dict) -> str:
    return c.get("combo") or f"{fname}::{c.get('arm', '?')}-seed{c.get('seed', '?')}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default="../ai-data-flywheel",
                    help="directory with logged *json flywheel outputs")
    ap.add_argument("--pattern", default="*.json")
    ap.add_argument("--out", default="./refs")
    ap.add_argument("--mode", default="tier", choices=["tier", "catxtier"])
    ap.add_argument("--dose-cap", type=float, default=0.25)
    ap.add_argument("--fdr", type=float, default=None,
                    help="BH FDR level for frontier flips (default off = Wilson-only)")
    args = ap.parse_args()

    logdir = Path(args.logs)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    files = sorted(logdir.glob(args.pattern)) if logdir.exists() else []
    if not files:
        print(f"No files matched {logdir}/{args.pattern} — writing empty report.")
    items: list = []
    for f in files:
        # skip our own outputs + test fingerprints
        if f.name in ("retro_ledger.json", "expected.json", "probe_ref.json",
                      "colab_gpu_results.json", "bottleneck_validation.json"):
            continue
        items.extend(load_combos(f))

    per_combo = []
    for fname, c in items:
        rid = combo_id(fname, c)
        try:
            doc = cl.build_ledger(c["rounds"], run_id=rid,
                                  mode=args.mode, dose_cap=args.dose_cap,
                                  fdr=args.fdr)
        except Exception as e:  # never let one malformed run kill the census
            print(f"FAIL {rid}: {e}")
            continue
        per_combo.append({
            "run_id": rid, "file": fname,
            "arm": c.get("arm"), "seed": c.get("seed"),
            "nds": doc["nds"], "understatement": doc["understatement"],
            "frontier": doc["frontier"],
            "n_rounds": len(c["rounds"]),
        })
        # stash full doc for JSON output
        per_combo[-1]["_full"] = doc

    # ---- corpus summary ----
    nds_vals = [p["nds"]["nds"] for p in per_combo]
    summary = {
        "n_runs": len(per_combo),
        "mode": args.mode,
        "nds_mean": round(mean(nds_vals), 3) if nds_vals else 0.0,
        "nds_frac_gt0": round(sum(1 for v in nds_vals if v > 0) / len(nds_vals), 3) if nds_vals else 0.0,
        "nds_dist": dict(sorted(Counter(nds_vals).items())),
        "n_dormant_slices": sum(1 for p in per_combo for f in p["frontier"]
                                if f["harvest_path"] == "bank-regenerate-or-adapter"),
        "n_archive_importable": sum(1 for p in per_combo for f in p["frontier"]
                                    if f["harvest_path"] == "archive-import"
                                    and f.get("status") == "trailing"),
        "n_understating": sum(1 for p in per_combo if p["understatement"]["understates"]),
    }

    full = {"schema": cl.SCHEMA + "+retro/v1", "summary": summary,
            "combos": [{k: v for k, v in p.items() if k != "_full"} for p in per_combo],
            "ledgers": {p["run_id"]: p["_full"] for p in per_combo}}
    (outdir / "retro_ledger.json").write_text(json.dumps(full, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Wrote {outdir / 'retro_ledger.json'} ({len(per_combo)} runs)")

    # ---- markdown report ----
    L = [f"# Retro-ledger report ({args.mode} mode)", "",
         f"Runs: {summary['n_runs']} | mean NDS: {summary['nds_mean']} | "
         f"runs with NDS>0: {summary['nds_frac_gt0']} | "
         f"understating runs: {summary['n_understating']}", "",
         "NDS = fraction of slices where the final generation is NOT the "
         "frontier holder. Dormant = holder has zero importable mass "
         "(capability in weights, archive pruned).", "",
         "## Per-run NDS (top 30 by NDS)", ""]
    ranked = sorted(per_combo, key=lambda p: (-p["nds"]["nds"],
                     -max([f['regret_of_current'] for f in p["frontier"]] or [0])))
    L.append("| run | NDS | max regret | understates | trailing slices |")
    L.append("| --- | --- | --- | --- | --- |")
    for p in ranked[:30]:
        trail = ",".join(f["slice"] for f in p["frontier"] if f.get("status") == "trailing") or "-"
        mx = max([f["regret_of_current"] for f in p["frontier"]] or [0])
        L.append(f"| {p['run_id']} | {p['nds']['nds']} | {mx} | "
                 f"{p['understatement']['understates']} | {trail} |")
    L += ["", "## Dormant frontiers (holder has no importable mass)", ""]
    dorm_rows = [(p["run_id"], f) for p in per_combo for f in p["frontier"]
                 if f["harvest_path"] == "bank-regenerate-or-adapter"
                 and f["regret_of_current"] > 0]
    if dorm_rows:
        L += ["| run | slice | holder | regret | path |",
              "| --- | --- | --- | --- | --- |"]
        for rid, f in dorm_rows[:40]:
            L.append(f"| {rid} | {f['slice']} | {f['holder']} | "
                     f"{f['regret_of_current']} | {f['harvest_path']} |")
    else:
        L.append("_none with positive regret in this corpus_")
    L += ["", "## Falsification reading", "",
          "- NDS~=0 everywhere -> harvesting thesis empty in this regime; "
          "ledger survives as regression dashboard only.",
          "- NDS material + archive-importable trailing slices -> pkg20 "
          "(regret-weighted import A/B) is motivated.",
          "- Dormant-heavy -> parameter/adapter harvest or bank regeneration, "
          "not data import, is the binding path.", ""]
    (outdir / "retro_report.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Wrote {outdir / 'retro_report.md'}")

    # console verdict line (repo idiom)
    print(f"\nretro-ledger: {summary['n_runs']} runs, mean NDS {summary['nds_mean']}, "
          f"understating {summary['n_understating']}, "
          f"dormant {summary['n_dormant_slices']}, "
          f"importable-trailing {summary['n_archive_importable']}")


if __name__ == "__main__":
    main()

# AI Data Flywheel — lightweight simulation platform

A pure-Python (stdlib-only, plus numpy for one transfer experiment) simulation
of the model-on-model training loop: synthetic data generation, rule-verified
filtering, distillation-style transfer, and selective reuse of prior
generations. Domain: short chain-of-thought traces + final answers for
verifiable math/logic problems (procedural bank included).

The headline result of the program: synthetic-data feedback systems are
**capability-preservation and information-routing systems** — failure comes
from interactions among evaluator reliability, selection pressure,
capability-dependent data supply, archive composition, training-pool
bottlenecks, and inherited model state. Per-package reports (`*_report.md`)
record every accept/reject decision with replication status.

## Frozen doctrine (do not reopen without a clear contradiction)

- Scorer v4 (fixed expression evaluator + coverage term); blind judge with
  agreement/bias-gated mixing (default-on); recency-36 training pools
  (top-N-per-tier once skills stop transferring); single parent (merge only
  above complementarity 0.5); length-bin cap hygiene; probe + provenance
  tripwires; procedural bank with fresh-seed probes.
- Incident response: multi-channel tripwires, first-fire-wins →
  diagnosis-matched joint repair (length regularization for compounding decay;
  quarantined generation reset for coordinated-error lock-in). Never roll back
  without quarantine; re-score pools on any judge change.

## Layout

- `flywheel_sim.py` — domain, SimulatedModel, generation, rule verifier, training.
- `flywheel_harness*.py` — Threads A/B/C experimental series (selection × judges × collapse).
- `flywheel_threadC.py`, `flywheel_pkg1.py` … `flywheel_pkg18.py` — follow-up packages.
- `flywheel_bottleneck.py`, `flywheel_kit.py` — capability-mass accounting + tested incident-response kit.
- `flywheel_lm.py` — gradient transfer testbed (tiny numpy MLP; needs numpy).
- `tools/make_refs.py` — regenerates tracked references (`refs/`, `tests/expected.json`).
- `tests/` — pytest suite (unit + bit-identical reproduction).
- `*_report.md` — per-package research reports (tracked documentation).
- Result JSONs (`*_results.json`, `pkg*.json`, …) are **generated data**: excluded
  from version control via `.gitignore` (deterministically reproducible — see below).

## Install

```bash
pip install -r requirements.txt   # numpy, pytest (stdlib only otherwise)
```

Python ≥ 3.10. Verified on 3.12.

## Quickstart (fresh clone, < 2 min to green)

```bash
python -m pytest tests/ -q        # 17 tests: units + bit-identical fingerprint
python flywheel_sim.py            # base R0-R6 flywheel demo
```

## Full reproduction (in order; seeds fixed, expect ~1–2 h total)

```bash
python flywheel_sim.py
python flywheel_harness.py             # v1: 15 combos x 7 rounds
python flywheel_harness2.py            # v2: fixes + ramp + import
python flywheel_harness3.py --block sanity && python flywheel_harness3.py --block adv \
  && python flywheel_harness3.py --block seed && python flywheel_harness3.py --block scorer
python flywheel_harness4.py --block gap && python flywheel_harness4.py --block misc \
  && python flywheel_harness4.py --block cov
python flywheel_harness5.py --block worst && python flywheel_harness5.py --block rescue \
  && python flywheel_harness5.py --block gapseed && python flywheel_harness5.py --block baseline
python flywheel_threadC.py --block c_normal && python flywheel_threadC.py --block c_collapse \
  && python flywheel_threadC.py --block c_parents && python flywheel_threadC.py --block c_misc
python flywheel_pkg1.py --block p1_normal && python flywheel_pkg1.py --block p1_collapse
python flywheel_pkg2.py && python flywheel_pkg3.py --block base \
  && python flywheel_pkg3.py --block trap && python flywheel_pkg3.py --block break
python flywheel_pkg4.py && python flywheel_pkg5.py --block s0 \
  && python flywheel_pkg5.py --block s1500 && python flywheel_pkg5.py --block s3000
python flywheel_pkg6.py && python flywheel_pkg7.py && python flywheel_pkg8.py
python flywheel_pkg9.py && python flywheel_pkg10.py && python flywheel_pkg11.py
python flywheel_pkg12.py --block s0 && python flywheel_pkg12.py --block s1500 \
  && python flywheel_pkg12.py --block s3000
python flywheel_pkg13.py --block starved && python flywheel_pkg13.py --block banked
python flywheel_pkg14.py && python flywheel_pkg15.py && python flywheel_pkg16.py  # (asserts: superseded design, see pkg17)
python flywheel_pkg17.py && python flywheel_pkg18.py
python flywheel_bottleneck.py && python flywheel_kit.py   # self-validates 9/9
python flywheel_lm.py && python flywheel_lm.py --arms bias --out lm_bias.json \
  && python flywheel_lm.py --arms gatedbias --out lm_gatedbias.json
```

Notes: `pkg16` asserts by design (its guard rejects the unconstructible narrow
premise — documented in `pkg17_report.md`); several scripts append console logs
(`*_console.txt`, git-ignored). Runtimes range from seconds (unit packages) to
~10 min (gradient sweeps).

## Determinism policy

- All randomness is explicitly seeded (`random.Random` / `numpy SeedSequence`
  streams); no `hash()`-dependent control flow in library code; no wall-clock
  or dict-order dependence in any scored path.
- Verified: the suite passes bit-identically under `PYTHONHASHSEED=0`, `12345`,
  and unset. Set `PYTHONHASHSEED=0` in CI for belt-and-braces.
- `tests/expected.json` pins exact outputs; regenerate deliberately with
  `python tools/make_refs.py` after INTENDED changes and review the diff.
- Known caveat (documented, contained): one 1-artifact G0 shift was once
  observed between turns from a base-file micro-edit; fork-validity was
  unaffected. Fingerprint G0-kept signatures on any future occurrence.

## Live-model tracks (Ollama pilot + GPU SFT)

- `flywheel_pilot.py` — qwen2.5:1.5b generation wired into the scored-artifact
  loop (control / invert / gated / gated_noisy arms); `pilot_report.md`.
- `tools/sft_loop.py` — LoRA SFT diets (clean / poisoned / expert) + probe eval;
  needs `requirements-sft.txt` (dedicated venv recommended, see SFT notes).
- `tools/colab_expert_cell.py` — the same expert-diet cell as run on Colab T4
  (single self-contained cell); `tools/emit_colab_cell.py` regenerates it from
  `tools/W_bank.json` + `tools/Z_probe.json` (procedural banks, git-ignored,
  rebuildable via `flywheel_pkg9`).
- GPU SFT results: `lm_bias_report.md` + `refs/colab_gpu_results.json`
  (expert/clean help modestly; coordinated poison floors; local-CPU degradation
  is a separate recipe/hardware regime).

## Capability ledger (multi-model contribution, consolidated)

- `capability_ledger.py` + `retro_ledger.py` + `demo_make_logs.py` — adopted
  canonical implementation (sibling Muse-Spark session): per-slice C/M
  matrices, Wilson-gated frontiers, NDS, dormant census, harvest paths.
- `pkg19_ledger_report.md` — design (Ling session) completed with measured
  numbers on this repo: NDS 0.0 (healthy shared-skill) / 0.25 (collapse) /
  0.413 (forgetting regimes); independent Nemotron rerun reports 0.81.
- `refs/ledger_census.json` — pinned full-corpus numbers above, Wilson-only
  and BH-FDR gated (identical: FDR changes zero cells on current data).
- `tests/test_ledger.py` — adopted suite (green); Big Pickle's variant test
  targets an unsupplied API and was excluded with documented reason.
- Run: `python demo_make_logs.py && python retro_ledger.py --logs ./demo_logs --out <tmpdir> --mode tier`.

## License

MIT — see `LICENSE`. Optional next step: CI workflow running `pytest` with `PYTHONHASHSEED=0`.

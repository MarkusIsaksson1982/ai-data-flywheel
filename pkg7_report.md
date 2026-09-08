# Package 7 report — Playbook vs misconception lock-in: detection generalizes, treatment doesn't

12 rescue runs (4 arms × 3 seeds, forked from verified locked prefixes:
G5 misc 0.30–0.52, corr 0.08–0.25) + tripwire-ordering log. Data: `pkg7_lockin.json`.
Note: flat-protocol lock-in equilibrates at misc ~1/3 (majority needs collapse
pressure, v4) — still a valid locked state: corr ≤0.25, probe ≤0.29.

## Tripwire ordering is failure-class-dependent (generalizes with flipped priority).

First-fire per channel on prefixes — s0: kept_misc G0, wrongmode G0, probe_ref
G1, gate G1; s1500: probe_ref/kept_misc/wrongmode G0, gate G1; s3000:
probe_ref/wrongmode G0, kept_misc/gate G1. Drift never fires. For compounding,
probe led; for lock-in, misc-channels fire at G0 — before any probe drop. The
generalizable pattern is the multi-channel suite with first-fire-wins, not any
single tripwire: something always fires by G1, but WHICH channel leads depends
on the failure class.

## Rescue: nothing recovers from deep lock-in — including judge repair.

G13 endpoints (main / misc-rate): A 0.19/0.49, 0.19/0.53, 0.22/0.36; B 0.22/0.40,
0.22/0.53, 0.31/0.23; C 0.33/0.28, 0.17/0.43, 0.42/0.20; D 0.06/0.48, 0.08/0.60,
0.14/0.42. Recovery bar (0.65 + misc<0.05) unmet on all 12 runs.

- B falsifies the naive v4 extrapolation ("blind purges misc"): purge requires
  correct-mass ≥ kept-size. Below ~0.3 correct, even a perfect rule filter
  re-selects poison (kept_misc 0.28–0.50 throughout) and the loop holds. Judge
  repair is necessary but insufficient in deep collapse.
- C (length regularization) is near-irrelevant here — misc arts have normal
  lengths — yet posts the best numbers (kept_misc 0.11–0.17) via the temp clamp
  and rule-ranked pools, still far from recovery.
- D is actively worst (probe → 0.0 on s1500): length-filtered pools under
  poisoned selection concentrate the flaw.
- Missing piece, diagnosed but unrun: GENERATION repair — a fresh capable model
  (golden reset with quarantined pool), since no selector can select what the
  degraded model never generates. v5-C failed on pool contamination, not on the
  reset concept; quarantined-reset remains the open arm.

## Verdict on the playbook question.

Does "reference tripwire → forward regularized treatment" generalize? Half:
detection generalizes (augmented suite fires by G1 on both failure classes,0 FP
record intact — no healthy false fires anywhere in the program); the fixed
treatment does not transfer (length regularization is compounding-specific;
misc needs generation repair). Adopt instead: **multi-channel tripwires with
first-fire-wins PLUS a diagnosis-matched response library** (compounding →
length regularization; lock-in → judge repair, escalating to quarantined
reset). The reusable pattern is detect-broadly-then-match, not one playbook.

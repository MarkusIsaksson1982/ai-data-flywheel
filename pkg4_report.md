# Package 4 report — Compounding errors break the margin rule structurally

12 combos (4 arms × 3 seeds, 6 normal rounds). Data: `pkg4_comp.json`.
Complexity increase: `compound_growth` (guarded, default 0) makes per-step
accuracy decay geometrically with step position — long chains disproportionately
wrong, verified sign flip (len→corr {1:.0,2:.4,3:.68} at 0 vs {1:.5,2:.41,3:.3}
at 0.35). Verbosity now anti-correlates with correctness by construction.

## Dose–response at G5 (means over seeds; the margin rule falls monotonically).

| arm | main | probe | keptlen | lencorr sign |
|---|---|---|---|---|
| control | 0.870 | 0.875 | ~2.0 | + (longer=better) |
| comp30 | 0.500 | 0.597 | ~2.1 | − (mostly) |
| comp80 | 0.426 | 0.389 | ~2.1 | − |
| comp-guard | 0.537 | 0.541 | ~1.8 | − |

Control improves 0.42→0.87 while comp80 degrades 0.37→0.43 from near-identical
starts: the flywheel AMPLIFIES the generator flaw in both directions —
selection for length under compounding is selection for wrongness, and training
compounds it. This is the first verbosity-driven quality collapse in the
program, and it required wrongness to coincide structurally with the rewarded
trait, exactly as the Package 3 autopsy predicted.

## Probe leads the collapse (2/3 seeds).

Extra-step probe variants are hypersensitive to compounding: comp80-seed1500
probe hits 0.167 at G2 while main is still 0.389; seed3000 G2 probe 0.292 vs
main 0.611. Probe-then-main ordering holds where it matters (early rounds);
by G5 both are down (probe 0.389 < main 0.426 — the gap inverts the healthy
direction). The probe set earns its keep as a leading indicator here, after
three packages of correct silence.

## Guardrail: partial mitigation, principled limit.

comp-guard (0.537) beats comp80 (0.426) but barely beats comp30 (0.500) — the
length cap limits long-chain concentration yet compounding degrades 2-step
chains too (growth hits step index 1 at 0.65×), and novelty cannot help when
every long path is poisoned. Selection-side guardrails cannot fix a shifted
generator distribution; the fix would have to be in training (e.g.
step-position-aware scoring) or the generator itself.

## Tripwire record: outcome tripwires catch it, judge tripwires cannot.

Drift never locks (max 0.254 — template space stable during quality collapse,
same lesson as misc lock-in); gating fires only blind-noise 0.8s (the judge
reports low rule scores faithfully — the failure is in SELECTION ranking, which
gating cannot see); wrongmode stays silent (perturbations don't coordinate).
Only the probe — an outcome tripwire on held-out data — marks the failure, and
early. Architectural lesson: judge-agreement monitoring is blind to
selection-proxy failures by construction; outcome probes are non-optional.

## Decisions.

- The margin rule is now bounded, not broken in general: it holds whenever
  errors are position-independent perturbations, and falls exactly when
  wrongness correlates structurally with the selected trait. Both regimes are
  now demonstrated with mechanisms.
- No default changes (growth stays 0, trap stays 0, fixed temp); ADD
  compound_growth>0 to the standard stress toolkit alongside invert+misc.
- Highest-value next question: recovery from compounding decay (can
  step-aware scoring or length-regularized training rebuild, or is the decay
  absorbing like misc lock-in?) — and whether the probe lead generalizes to a
  stopping rule (halt/revert when probe drops 2 straight rounds while main holds).

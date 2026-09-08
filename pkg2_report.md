# Package 2 report — Goodhart: clean negative with a quantitative mechanism

9 combos (3 arms × 3 seeds, 6 normal rounds). Data: `pkg2_goodhart.json`.
Probe: 12 held-out variants (Q01–Q06 surface, Q07–Q12 structural), 24 arts/round,
never trained on. Pressure: rank by proxy = rule + 12·len(cot); guarded adds
+15·novelty with a per-length-bin cap of 8.

## Q1. No proxy–true divergence obtainable: proxy, main, and probe move together.

G5 means over seeds — main corr: control 0.874, goodhart 0.880, guarded 0.880;
probe: 0.875, 0.931, 0.875; gaps all within ±0.15 with no arm-wise trend.
keptlen separates only slightly (goodhart 2.11–2.22 vs control 1.89–2.06 vs
guarded ~1.6): the generator's verbosity range (1–4 steps, distractors rare)
gives the pressure almost nothing to grip. Mechanism, quantitative: max
verbosity differential ≈ 3 steps × 12 = 36pts < ~60pt correct/wrong gap — the
same margin story as v3/v4. Below-gap proxy weights cannot flip selection;
this pressure was doomed by arithmetic visible before running. A divergence
would need either a generator that trades correctness for fluency or a
gap-exceeding weight (which would degrade main and probe together — uniform
damage, not a gap).

## Q2. Rediscovery is the healthy steady state — provenance needs a control.

dup_high reaches 0.94–1.0 and new_path 0.0 by G5 in ALL arms *including
control*: the signature space (canonical equations over 12 problems) saturates
by construction. Without the control baseline these readings would falsely
scream Goodhart. Detection rule: only a *divergence* between arms in
dup/newpath (or a probe gap) counts — never the absolute level. (Guarded does
hold new_path higher through G1–G3: 0.35/0.41 vs 0.22/0.33 — the novelty bonus
mechanism works; it just has no capability consequence here.)

## Q3. Guardrail: harmless, unproven as protection — adopt as hygiene.

The length-bin cap binds (guarded keptlen 1.6 vs 2.2, proxy ~110 vs ~126) at
zero capability cost (main/probe match). Adopt the cap + novelty bonus as cheap
default hygiene; do not claim it prevents Goodhart — nothing here tested it.
The protection test that would: a gap-exceeding adversary (invert-class, v4/v5
machinery already supports it) against guarded selection.

## Decision.

REJECT proxy-optimization as a live risk in this domain/pressure range; KEEP
the probe set + provenance tracking as permanent tripwires (they cost one
generation batch per round and caught nothing — which is what tripwires are
for); ADOPT the length-bin cap as style hygiene. Next Goodhart work, if any,
belongs on a generator with a real fluency–correctness tradeoff, not here.

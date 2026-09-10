# Package 29 — WQ5-sim: mass drives skill, length drives depth, probe compounds both

## Design
Base SM [0.80, 0.90, 0.55]; med/easy pools fixed-full; hard pool varies (correct,
rule-verified): H0/H2/H6/H12 (mass ladder) + H12-short/H12-long (chain-length split,
pre-registered). 3 rounds on FIXED pools, blind, probe/round. `python
flywheel_pkg29.py` → `pkg29_dose.json`.

## Result: double dissociation + compounding readout
- Tier_acc[2]: H0 0.55→0.47→0.39 (forgetting); H2/H6/H12/short/long IDENTICAL
  0.55→0.753→0.864. Dose threshold for SKILL ≤ 2 correct arts — pure presence.
- Depth: H12-long 2.28→2.35 (rises); H12-mixed →2.03; H12-short →1.94; H2/H6/H0
  →1.87. Depth tracks CHAIN LENGTH only; mass ladder identical at every level.
- Probe-hard G2: H0 0.125–0.375; all mass arms 0.438–0.562 regardless of length.
  Length moves depth 1.94→2.35 with ~zero probe consequence at fixed skill 0.864.
- Reconciliation with pkg28 (depth 2.1→2.6 gave probe 0.312→0.938): probe ≈
  skill^depth compounding — pkg29 holds skill fixed (depth-only moves little);
  pkg28 moved both (skill 0.936→0.997 AND depth 2.1→2.6 → big moves). Joint
  function, no contradiction. Implication: probe-hard is a steep readout where
  small param gaps compound into large score gaps — more reason for Wilson gating,
  less reason to treat probe deltas as linear capability deltas.

## WQ5-sim verdict (feeds CONSULT-2)
Hard-tier SFT needs LONG CORRECT CHAINS in volume (length × mass), not mass alone:
36 short-but-correct traces saturate skill yet leave depth — and hence hard probe —
flat. A blind 100-trace escalation is the wrong design; a long-chain dose is the
candidate. SFT long-dose motive narrowed (not closed): dose×LENGTH, unknown threshold.

# Package 8 report — Quarantined reset breaks deep lock-in (first verified cure)

12 runs (4 arms × 3 seeds, forked from verified locked prefixes:
G5 misc 0.30–0.52, corr 0.08–0.25). Data: `pkg8_reset.json`.
A/B replicate pkg7 bit-identically (s0 G10–G13 match to 3 decimals) —
cross-turn determinism confirmed twice over; comparisons are valid.

## Q1 (fresh SM0 + golden + screened-early pool, screened recency after): RECOVERS.

G13 (main / probe / misc): s0 0.778/0.708/0.0, s1500 0.639/0.458/0.0, s3000
0.778/0.667/0.0. kept_misc 0.0 on every round of every seed — the poison never
re-enters. Recovery bar (≥0.65 + misc<0.05): 2/3 outright; s1500 at 0.639 and
climbing (0.361→0.528→0.444→0.639), i.e. one more round short, not stalled.
Notably the screened pools are SMALL early on (16–35 arts vs full 36 — quality
over quantity), and G10 starts at fresh-model level (0.36–0.56): this is genuine
rebuilding across 4 rounds, not an instant fix. First intervention in the
program to break deep lock-in with misc fully purged on all seeds.

## Q2 (fresh SM0 + unscreened pools): reinfected — quarantine is load-bearing.

misc re-enters by G11 on all seeds (0.23/0.29/0.15) and kept_misc stays >0;
mains stagnate 0.36–0.56; s1500 probe hits 0.042. Reset alone replicates the
v5-C failure exactly: a fresh model drinking from a poisoned archive re-locks.
The cure is reset × quarantine, neither alone (Q2 fails; B stagnates 0.22–0.31).

## Updated incident-response doctrine (replaces pkg7's open arm).

For coordinated-error lock-in: multi-channel tripwire (misc-channels lead at
G0, probe-reference confirms) → judge repair is INSUFFICIENT in deep collapse
(purge needs correct-mass ≥ kept-size — now measured twice) → quarantined
generation reset (fresh params + golden/screened-only data, screened
continuation) → expect 3–4 rounds to rebuild, probe lagging main by ~1 round.
Do not reset without quarantine; do not trust unscreened archives post-incident.

## Open residue (honest, narrow).

s1500 needs a 5th round to cross 0.65; probe lags main in recovery (0.458 vs
0.639) — probe-as-recovery-gate would declare victory late. Single next run if
any: extend Q1 two rounds on s1500 to confirm the cross, plus a pooled-seed
estimate of rebuild time (current n=3 suggests 3–5 rounds).

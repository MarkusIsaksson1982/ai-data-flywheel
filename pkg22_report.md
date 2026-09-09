# Package 22 report — Dose caps are inert without screening; golden freezes gains in place

9 runs (A disease / B dose-unscreened / C dose+screened+golden × seeds 0/1500/3000;
invert pure0 throughout, wide 72/144, misc 0.35). Data: `pkg22_dose.json`.
Pool semantics locked by `tests/test_pkg22_pools.py` BEFORE the run (the one
time this program pre-registered a mechanism check — it paid off twice, below).

## Dose without screening does nothing (B ≡ A bit-identically, all seeds).

B pools (12/tier unscreened from invert-kept) vs A pools (top-36 wrongest):
different sets, identical tier-correctness profiles (hard: all wrong; easy/med:
mostly wrong) → identical updates → identical trajectories to 3 decimals
(acc pinned ~0.3-0.46, misc lingering). Caps filled with poison train poison.
Dose alone is inert — a second, independent null beside pkg11-B.

## C recovers then freezes — via golden, not via sustained hard practice.

C: acc 0.45 → 0.70-0.72 by G6, then EXACTLY flat (s1500/s3000 identical vectors
two rounds running). Forensics (post-hoc pool rebuild from JSON): early pools
carried screened all-correct hard (the dose+screen working as designed), but by
G6 pools are 24/24 golden — untiered, hence invisible to tier learning
(`tier` key absent → tier block skips) while sustaining shared skills
(arithmetic_acc 0.625 → 0.647 on golden). So golden backfill acted as a
PRESERVATIVE (froze gains, blocked both further rise and forgetting-decay),
not as a teacher. The jump itself (→0.70) came from screened hard while it
lasted; the hold comes from golden. Mechanism verified, not assumed.

## Two process findings (kept, since both generalize).

1. Pre-registered pool semantics (written before the run) caught a real
   inversion bug during development (swapped B/C screening) that console
   inspection had already misread once. Mechanism tests before runs: adopted
   as standard practice.
2. A mid-analysis "contradiction" (flat acc where forgetting predicted decay)
   resolved into the tier-blind-golden mechanism above — the report's first
   draft blamed the wrong cause (pool starvation). Forensic recomputation from
   stored artifacts beat console reasoning twice in this package.

## Verdict: the full chain, each link evidenced somewhere.

Bank (selection quotas put hard in the archive — pkg11) → screen (rule +
non-misc filter out poison — here: screened pools all-correct) → dose (quotas
survive the pool cut — pkg12, here: 12-hard slots filled) → train. Break any
link (A: no quota; B: no screen; pkg11-B: no dose) and hard skill pins at
~0.3. Golden is approved as backfill/preservative with the tier-blindness
documented (a tier-stamped golden would keep teaching — specified, unrun).

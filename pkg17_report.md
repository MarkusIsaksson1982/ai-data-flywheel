# Package 17 report — Compositional routing without enumeration (wide regime)

9 runs (3 arms × 3 seeds; prefix: misc + invert + tier skills at 50% kept;
fork G5–G7). Data: `pkg17_wide.json`. Supersedes the pkg16-narrow attempt,
whose guard correctly rejected an unconstructible premise (narrow top-k crowds
misc out: 0.35→0.05 — mechanisms interfere destructively across kept-fraction).

## Legs coexist partially at 50% kept; all tripwires fire by G2.

Prefixes: misc sustained 0.09–0.16 (kept_misc up to 0.47), jcorr ≈ −0.99,
hard lagging (harddiv fires G1–2), probe_ref fires at G0. poolhard0 NEVER fires
here — hard is present-but-wrong, so that channel is regime-blind; harddiv
covers it. Tripwire lesson refined: no single channel is necessary across
regimes, but the SUITE (first-fire-wins) has now fired on every failure class
tested: compounding (probe), lock-in (misc-channels), compositional (all).

## Routing: joint response uniquely recovers; singles fail distinctly.

G7 hard-acc (acc2) by arm, seeds 0/1500/3000:
A 0.393/0.381/0.382 (pinned; kept-hard corr 0.0 throughout) ·
B 0.393/0.381/0.382 (gate purges misc to ~0 and lifts kept-hard correctness to
0.53–0.75, yet acc pinned — pool re-starves hard to 0–1, pkg11 mechanism) ·
D 0.846/0.835/0.836 (kept_misc 0.0, kept-hard corr 0.83–1.0, poolhard steady 12,
probe-hard 0.44–0.56).
B proves the gate works (bias trips alpha 0.8 on all seeds; misc purged) while
proving it insufficient (hard skill needs pool supply). D proves joint
sufficiency — steep slope (0.46→0.84 in 3 rounds) from a screened 12-hard pool
(D-s3000 recovered identically starting from only 8 screened hard). No
combination enumeration was needed: match every firing channel, once each.

## Verdict: the diagnosis library graduates to general.

Routing composes: single-channel fixes fail on the other channels' terms
(B starves hard; C — pkg14 — poisons quotas), the joint response recovers on
all axes simultaneously. Standing doctrine gains one line (score hygiene
across judge switches, observed here as G5 pool contamination flushing by
G7) and one correction (poolhard0 is narrow-regime-specific; harddiv is its
wide-regime counterpart). Next single question: D to asymptote under the
blanket (does joint response reach 0.9+, pkg15-style?), or accept 0.84 at G7
as sufficient evidence and close compositional work.

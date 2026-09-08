# Package 12 report — Pool quotas survive scarcity; selection quotas don't (2×2)

12 runs (4 arms × 3 seeds, forked at the floor: hard acc 0.30, hard corr
0.02–0.21; scarcity = kept 12/round + pool cap 24). Data: `pkg12_scarce_{s0,
s1500,s3000}.json`. Recovery = hard acc ≥ 0.60.

## Only the both-quota cell recovers — for two distinct starvation reasons.

| arm | sel quota | pool quota | G9 acc2 | poolhard | verdict |
|---|---|---|---|---|---|
| A neither | — | — | 0.30 ×3 | 0 | floored |
| B pool-only | — | 8/tier | 0.30 ×3 | 0 | floored (unfillable quota) |
| C sel-only | 4/4/4 | — | 0.30 ×3 | 0 | floored (cut discards) |
| D both | 4/4/4 | 8/tier | 0.615→0.788→0.883 | 4→8@1.0 | **recovers G7 all seeds** |

- B fails for lack of CANDIDATES: plain selection keeps 0 hard, so the pool
  quota reserves empty slots (pools run 16/24 full). A quota the pipeline
  cannot fill is not a quota.
- C fails for lack of SLOTS: 4 hard kept/round (12 candidates) are all cut by
  the unstratified top-24 pool — pkg11's mechanism reproduced under scarcity.
- D works because each quota fixes the other's failure: selection supplies 12
  hard candidates, the pool reserves 8 slots, all filled at corr 1.0, and acc
  climbs 0.30→0.615→0.788→0.883 identically on all seeds. Hard corr ends
  0.44–0.52; probe-hard 0.31–0.50 (held-out recovery, partial as in pkg10/11).
- A/B/C probe-hard decays to 0.0–0.31: held-out hard capability erodes in
  parallel — scarcity starves generalization too.

## Verdict: recovery mechanism survives real data poverty.

Quotas must span the FULL pipeline — select with quotas AND pool with quotas;
either link alone re-imposes starvation through a distinct, measured mechanism
(empty reservation vs cut discard). Doctrine update (final form): under
non-transferable skills, the default training pool is top-N **per tier** from
history with per-tier selection floors sized so quota × window ≥ pool reservation;
unfilled reservations shrink the pool (accepted: smaller clean pool beats padded
dirty one — B's 16-art pools did no harm). Easy tier still untaxed throughout.
Next single question (escalation ladder per brief): capability-conditioned
valuation U(D|M,C) — price archive items by the skill slice at risk — now has
a measured substrate (tier_acc gaps) to condition on; or compositional failure
(hard-tier forgetting + misconception together) to test diagnosis matching.

# Package 11 report — Quotas recover hard skill, but only above the pool-survival threshold

9 runs (3 arms × 3 seeds, forked at the forgetting floor: hard acc 0.30,
hard corr 0.02–0.21). Data: `pkg11_recover.json`. Question: recover or merely
slow the fall? Answer: **recover — but the quota must survive the training
pool cut, not just selection.**

## Equal quotas (6/6/6) are bit-identical to plain top-k: a second null.

A and B match EXACTLY every round, all seeds (hard acc pinned 0.3, hard corr
0.2–0.3, probe-hard ≤0.31). Post-hoc pool recomputation explains why: B's pools
contain **0 hard arts** — the quota is nullified one level up. Mechanism,
measured: v4 scores every correct full-chain artifact exactly 100.0 regardless
of tier, so 18 easy + 18 med saturate the top-36 pool cutoff at 100.0 while
B's hard kept (top 96.3 — near-perfect, verified) are all discarded. Selection
quotas without pool quotas are theater.

## Hard-heavy quotas (4/5/9) recover: acc 0.30 → 0.615 on all seeds.

C's pool admits 9 hard arts, all correct (cutoff drops to 92.0), and acc jumps
exactly per the update rule (0.55·0.3+0.45·1.0 = 0.615). Hard corr G9:
0.333/0.250/0.396 (vs 0.21–0.25 control); probe-hard 0.375/0.438/0.312 —
recovery generalizes held-out. Partial, as in pkg10 (hard ≈ 0.3 vs easy ≈ 1.0).
Dose threshold sits between 6 and 9 hard keeps/round given a 36-pool over a
3-round window: the quota must leave pool slack that easier tiers cannot fill.

## Verdict: recover, with the quota placed correctly.

Stratified recovery from the floor is real (not merely slower falling — A/B
never leave it). Doctrine update, precise: **stratify the POOL builder, not
(only) the selector** — e.g. top-N per tier from history — and size quotas
against the pool cutoff (hard quota × window ≳ pool size − saturated easier
mass), because tier-blind score ceilings otherwise re-impose starvation at the
pool cut. Easy tier again pays nothing. Next single question: does the same
pool-level quota rescue hold under active collapse pressure (k-cut + forgetting
together), where pool slots themselves go scarce?

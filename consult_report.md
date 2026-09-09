# Consult-control report — are pkg21 merge gains retrieval-bound? (frozen platform)

Question (pkg19-roadmap consultation control, ChatGPT): when an old model still
helps, is that "historical information can be internalized" or merely "old
model is consultable"? Post-hoc over `pkg21_merge.json`, zero new compute.

## Method

For each arm/seed: rebuild training pools from arm-round kept (top-36 recency
by final, the documented builder family), split the G7 batch into KNOWN
(correct answer present in those pools) vs NOVEL (absent), and compare merged
(slicemerge) vs single accuracy on each split. Caveat, signed: prefix pools
(G0–G3) are excluded (not stored in arm entries), so NOVEL is an upper bound on
true novelty. Direction of bias analysis: omitted prefix knowledge can only
inflate the novel subset with actually-known problems for BOTH arms — but
asymmetrically favors merged (H-prefix hard knowledge). A zero gap therefore
stands; only a merged>single gap would need prefix-controlled confirmation.

## Result: gains are retrieval-bound; no internalization gap.

| seed | novel n (s/m) | novel-acc single | novel-acc merged | known-acc both |
|---|---|---|---|---|
| 0 | 66 / 60 | 0.470 | 0.483 | ~0.94 |
| 1500 | 63 / 63 | 0.492 | 0.492 | ~0.97 |
| 3000 | 72 / 69 | 0.472 | 0.449 | ~0.91 |

Merged-vs-single on NOVEL: +0.013, 0.000, −0.023 — null. Everything the merged
weights demonstrate on G7 is already capturable by answering from pool
knowledge where present (known-acc ~0.95 both arms). Param averaging added no
beyond-retrieval capability in this regime.

## Verdict and reframe.

The pkg21 "merge win" over single was a DATA-ACCESS win wearing merge
clothing: single was denied H-branch pools by design, merged received them.
The fair single baseline with H data is exactly what pkg11/12 quota-pool arms
already measured — consistent story, no contradiction. For THESE skills
(verifier-anchored arithmetic with shared templates), harvesting (data import)
dominates merging (param averaging); the consultation control, not the merge,
is the correct comparator for any future harvesting claim. Internalized
beyond-retrieval gains remain undemonstrated on this platform — that absence,
now measured rather than assumed, is the finding.

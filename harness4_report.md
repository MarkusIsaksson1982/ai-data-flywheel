# Harness v4 report — decisive adversary, misconception lock-in, drift metric, coverage scorer

20 combos × 8 rounds (G0–2 normal, G3–5 ramp k=14/10/6, G6–7 recovery) in three
blocks: `gap` (10), `misc` (6), `cov` (4). Machine-readable: `harness4_{gap,misc,cov}.json`.
Base sim gained a guarded misconception model (`misc_rate`, default 0;
legacy RNG streams bit-identical — blind controls replicate v2/v3 exactly:
topk-blind-fixed05 G2 0.833/0.556, grid-blind-fixed05 G2 1.0/0.556).

## 1. Gap-inverting judge: the decisive test delivers quality collapse

`adv_invert`: j = 100 − 0.9·rule + N(0,5) (wrong ~15→~86, correct ~95→~15;
jcorr ≈ −0.99 everywhere — perfect anti-ranking).

- **pure0: total poisoning.** Kept correct-rate 0.0 at G2/G5/G6 (topk keeps
  0/18, 0/6, 0/18 correct; grid G6 0.11). Batch corr craters and stays down
  (topk G7 0.333, grid G6 0.278). Grid-invert-pure0 posts qM **−0.117** — the
  only negative quality margin in the program: worse than baseline.
  Coverage stays high (0.75–1.0): this is QUALITY collapse with coverage
  intact, the mirror image of v1/v2's coverage collapse. Collapse has two
  orthogonal axes; all prior runs explored only one.
- **fixed05 does NOT contain it, but doesn't catastrophize either.** Final ≈
  50 + 0.05·rule: the anchor degrades ranking to a weak signal, and top-k of a
  weak signal still enriches correct (kept 0.83–1.0 correct). Cost is modest but
  real (G7 0.694/0.583 vs blind 0.806/0.778; grid suffers more — it preserves
  wrong cell-champions).
- **gated097 contains it.** |bias| 20–70 trips the gate from G2 on (alpha 0.8
  throughout); kept stays 1.0 correct on topk; G7 0.833/0.667 ≈ blind. First
  regime where gating has large measured value — the v2/v3 "no downstream
  effect" verdict is updated: gating is insurance that pays exactly when the
  judge turns adversarial.

## 2. Misconception lock-in: coordinated error + selecting judge = absorbing state

Base-sim `_misc` artifacts: deterministic truth+1 answer, fixed phrasing,
fluent format (rule 15.0); `misc_rate` inherited toward the kept-set fraction.

- **misc0.35 × invert × pure0: full lock-in.** misc_rate 0.35→0.54 (majority by
  G7); kept truth+1 signature 11/18 at G6, 9/18 at G7; batch corr 0.25→0.083;
  rec=None — never recovers, an absorbing state. First genuine wrong-answer
  mode-lock in the program (perturbation noise could never coordinate this).
- **Same run under gated097: purge.** kept_misc hits 0 from G2, rate decays to
  0.032, signature 0/18, corr recovers to 0.722, rec=1. Detection (bias) +
  response (alpha 0.8) breaks the feedback loop.
- **fixed05: stalemate** (rate 0.35→0.106, corr flat ~0.4); **blind and even
  fluent-pure0: purge to ~0.01** — the +25 fluent bonus cannot promote 15-pt
  arts (margin mechanism, v3, confirmed again: kept_misc 0 throughout).

## 3. Drift-vs-baseline lock: selective where predecessors fired constantly

Locked rounds by phase over all 20 combos: **normal 0/60, collapse 15/60,
recovery 30/40.** Zero false positives in 60 healthy rounds (v2: constant fire;
v3-shipped: constant fire). Recovery locks more than collapse — hysteresis, not
noise: drift-vs-G0 (e.g. 0.0→0.24→0.11→0.17→0.21→0.52→0.49→0.47) jumps at deep
collapse and does not return. The metric marks the collapse *state including
its scar*. Adopt as specified (drift > 0.35 vs own G0 + same-argmax
persistence). Caveat: template-space drift missed the misc lock-in (drift
stayed <0.35 there — answer-space coordination without phrasing change), which
is why the wrongmode channel must ship alongside it.

## 4. Coverage scorer (v4): works as intended, adopt

v4 = fixed + coverage=min(1, len(cot)/len(canonical)), weights 60/15/10/5/10.
Kept chains lengthen (topk 1.83 vs 1.69, floor 1.92 vs 1.83), truncated keeps
fall (6/36 vs 9/36; 5/36 vs 7/36), G7 quality ticks up (0.806 vs 0.778; 0.833
vs 0.778), coverage identical. Small, no-harm, directionally right — the
lucky-guess loophole (R0-SM-0-011 class) now costs ~7pts. Adopt v4 as default;
percent/symbolic prose remains neutral by design.

## 5. Lineage

Versions `{policy}x{judge}x{alpha}x{import}x{scorer}xseed{off}xmisc{rate}-G{g}`;
artifacts carry `_misc`, scorer, seed fields; rounds store kept_ids, calib,
drift fields, kept_misc_frac, misc_rate. v4 unit checks (coverage math, TVD
identities, invert mapping) run before every block.

## 6. Takeaways

- Two collapse axes confirmed: coverage collapse (pressure, quality intact) and
  quality collapse (inverted selection, coverage intact). Monitor both; they
  need different responses (re-import vs judge quarantine).
- The margin rule is now quantitative: bias < gap reshuffles, bias > gap
  poisons, inversion kills. Gating's value is proven exactly in the kill regime.
- Coordinated error + selecting judge is absorbing; the defense stack is
  bias-triggered gating (purge verified 0.54→0.03) — fixed-weight anchors only
  stalemate.
- Ship: v4 scorer, drift-vs-baseline lock + wrongmode channel, agreement-gated
  mixing as default-on insurance.
- Open: gap-inverting judge *with* misconception under grid policy (worst-case
  combo, unrun); systematic-misconception *recovery* (can anything unseat an
  absorbing lock-in? longer re-import? golden reset?); multi-seed the gap block
  (±0.1 noise caveat from v3 still applies).

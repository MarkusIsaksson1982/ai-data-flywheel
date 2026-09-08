# Package 1 report — Divergent-parent merging: clean null, gate validated as filter

18 combos (3 arms × 2 protocols × 3 seeds). Data: `pkg1_{p1_normal,p1_collapse}.json`.
Method: shared G0, exploit (T0.55/top-12) vs explore (T1.2/top-24) branches G1–G2,
merge at G3 (matched 36-pools), single-parent continuation.

## Result: no measurable gain from divergent merging.

Endpoint means over seeds — normal G5 corr: single 0.870, pair_same 0.861,
pair_div 0.907 (Δ+0.037, inside seed noise ±0.08); collapse G7 corr: single
0.916, pair_same 0.907, pair_div 0.898 (Δ−0.018). Coverage likewise flat
(Δ −0.03 / +0.00). Per-seed gains scatter sign (−0.055…+0.083). pair_same
replicates the Thread-C null exactly.

## Mechanism: the manipulation never achieved divergence.

Branch kept-set complementarity at merge: 0.083 / 0.25 / 0.0 across seeds.
Temperature + selection-strictness changed the *quality mix*, not *category
coverage* — both branches cover ~all pids, so there was nothing complementary
to merge. The Thread-C >0.5 gate would have rejected all six merges: validated
as a filter, though its positive side (compl > 0.5 → gain?) remains untested
because no recipe here produced it.

## Decision: REJECT routine merging; KEEP the gate.

- Default stays single-parent. Merge machinery remains available but gated:
  compute complementarity first, merge only above 0.5, log the decision.
- Tension noted honestly: base-sim R6 (exploit×explore distill, 83→93) hinted
  the opposite — but that was one unseeded observation against six seeded
  nulls; the nulls win. A stronger divergence recipe (disjoint problem subsets
  per branch, or distinct objectives) is the only variant worth testing, and
  per the brief it is explicitly out of scope unless prioritized later.

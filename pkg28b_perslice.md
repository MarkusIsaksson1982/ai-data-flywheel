# Package 28b — Per-slice-budget matching: specialist edge does NOT survive (round5-ii)

## Design
`python flywheel_pkg28.py --per-slice`: every stream gets 144 calls (eco total 432
vs solo 144). Phase-1 fork identical (same fork states, deterministic). Answers the
diagnostic question; total-cost matching stays the external frame.
Out: `pkg28b_perslice.json`.

## Result (G6 probe-hard)
| seed | eco-joint | solo-C/M/F | consult | graft | pair-MF |
|---|---|---|---|---|---|
| 0 | 0.875 | 0.25/0.125/0.875 | 0.562 | 0.750 | 1.000 |
| 1500 | 0.812 | 0.125/0.25/0.812 | 0.375 | 0.750 | 0.875 |
| 3000 | 0.875 | 0.188/0.25/0.875 | 0.688 | 0.625 | 0.938 |

- Eco-joint == solo-frontier EXACTLY all seeds (0.875/0.812/0.875) while holding t0/t1
  ≥ HIGH (solos don't). "Specialist wins on-slice" was substantially budget artifact:
  at equal exposure the ecosystem matches the specialist home AND away.
- Consult (blended, same 432-call sourcing) trails eco 3/3 (0.562/0.375/0.688):
  purity premium replicates OUTSIDE the budget confound — the money result survives
  both matchings. MF matches/exceeds solo-frontier (1.0/0.875/0.938): mid+frontier
  mixing is depth-neutral-to-positive, cheap-volume mixing is what dilutes.
- Gate re-read: under per-slice matching eco ties (never beats) best-solo on t2 —
  still no emergence (E stays rejected), but the FAIL's "specialist dominance"
  carries the exposure parenthetical: ~0.06–0.19 of the gap is budget shape, the rest
  is specialist purity (still real: solo trains pure).

## Verdict mapping update
Joint-coverage claim UPGRADED from "wins coverage, loses on-slice" to "matches the
specialist everywhere it practices while covering what it drops" — strictly more
than any solo under either matching. R0-separation (purity over blending) now holds
under BOTH budget frames. Report BOTH matchings henceforth (they answer different
questions; this file is the per-slice one).

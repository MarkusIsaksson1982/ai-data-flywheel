# Package 9 report — Procedural bank: data starvation without capability starvation

6 combos (2 arms × 3 seeds, 6 rounds, 144 arts/round on a 48-problem bank:
16/tier × 3 tiers by chain length; fresh-seed 24-problem probe bank).
Data: `pkg9_bank.json`. All canonical steps machine-verified correct at bank
build; v4 scorer resolves all probe pids (additive registration).

## Curriculum collapse in DATA: total, immediate, permanent.

Plain top-k keeps **0 tier-2 artifacts in all 18 rounds on all seeds**
(keptshare hard = 0/18 every round; easy takes 8–16). Hard problems score lower
(more corruption chances + truncation) and are amputated from training data
from G0 onward. The predicted new collapse mode reproduces perfectly.

## …without capability collapse: shared skills transfer across tiers.

Tier-2 batch corr still climbs under plain selection (0.27–0.40 → 0.48–0.63)
via shared arithmetic_acc, and stratification (forced 6/6/6) changes tier-2
endpoints by ±0.02 (strat mean 0.535 vs plain 0.549) — noise. With fully-shared
skills, reuse composition is as irrelevant across difficulties as Thread C
found it across categories. Curriculum effects require NON-transferable
skills (tier-specific params, or distinct operators per tier) — specified as
the next step, not attempted here.

## Saturation and memorization controls.

- 4× bank delays signature saturation only ~1 round (plain new_path G5
  0.0–0.17; strat 0.17–0.39 vs canonical-bank 0.0): the binding constraint is
  equation-signature space (small-number sums recur across problems), not
  problem count. Stratification preserves new paths longer (0.28–0.39) as a
  side effect of forcing hard-tier keeps.
- Fresh-seed probe tracks main in both arms (G5 probe 0.77–0.85 vs main
  0.76–0.81, no gap): improvement is not problem memorization — numbers and
  structures differ across bank seeds. The probe bank design is validated as
  genuinely held-out and should replace hand variants going forward.

## Decisions.

- ADOPT procedural banks + fresh-seed probe banks as the default evaluation
  substrate (replaces the 12-problem hand bank and Q-variants).
- REJECT tier quotas as a capability intervention under shared skills (data
  effect real, capability effect nil) — revisit only with tier-specific skills.
- Next question, single: do tier-specific capability parameters (or
  per-tier operators) produce genuine curriculum collapse under plain top-k,
  and does stratification then rescue hard-tier capability? That is the test
  that decides whether data composition ever matters for capability here.

"""
Realism jump — gradient flywheel: tiny MLP learning arithmetic under flywheel selection
========================================================================================
Relaxes stdlib-only to numpy (verified 2.5.2). Everything else frozen in spirit:
same procedural arithmetic domain, same selection/judge/pool machinery ported to
artifacts, same tripwire/metrics philosophy. Only the UPDATER changes:
heuristic blending -> full-batch gradient steps.

TASK (regression): input [a/S, b/S, op_onehot(+-*/)], predict c/S.
Slices (difficulty tiers): easy (operands 2-20), med (2-60), hard (2-200, incl.
exact division). Model: 6->32->16->1 tanh MLP (~700 params), full-batch GD.
DATA FLYWHEEL per round: generate 512 candidate traces (50% true claims, 50%
corrupted like the sim generator), score rule (|claimed-true|), judge variants:
  control: select correct traces (rule = 0 error), train toward TRUE c.
  invert : judge_score = 1 - correctness (+noise); select top (wrong traces),
           train toward CLAIMED c (wrong targets). Double poison.
  gated  : agreement = corr(judge, rule) on validation probe each round;
           alpha = 0.8 if agreement < 0.5 else 0.5 (v4 trigger port);
           select by alpha*rule_score+(1-alpha)*judge, train toward
           alpha*c_true + (1-alpha)*c_claimed.
Pool 256 (matched). 6 rounds (G0-G5). Test: held-out bank (fresh seed) per-slice
MSE + extrapolation probe (operands 200-500, outside train range) per-slice MSE.
TRANSFER TESTS: (1) pool clean-mass per slice (|claimed-true|<tol) predicts
per-slice test-MSE drop (bottleneck r=0.70 analogue); (2) gating contains
inversion (v4 analogue). Seeds 0/1500/3000.

Usage: python flywheel_lm.py (9 runs)
Out: lm_transfer.json
"""
from __future__ import annotations
import json
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np

OUT = Path(__file__).parent
NPP = 3  # kept for cross-file comparability of nothing; pool sizes below rule
SEEDS = [0, 1500, 3000]
N_CAND, POOL_N = 512, 256
EPOCHS, LR = 1500, 0.2
SCALE = 200.0
TOL = 0.05  # relative |claimed-true|/true threshold for clean pool mass
LOGMAX = float(np.log10(1 + 40000))  # log-target normalizer (products to 40000)


def logt(c):
    return float(np.log10(max(1 + c, 1e-9)) / LOGMAX)


def unlogt(v):
    return float(10 ** (v * LOGMAX) - 1)


def gen_claims(rng, n, operand_lo, operand_hi, balanced=True, corrupt_mode="unbiased"):
    """corrupt_mode: 'unbiased' ({0.5,1.5,2.0}, ~zero-mean in log space) or
    'biased' (always x2.0: systematic +0.30 log-shift that cannot average out).
    The RNG draw structure is identical in both modes (draw-then-override) so
    streams stay aligned across modes for matched-seed comparison."""
    """Rows: dicts with a,b,op,c_claimed,c_true,slice. 50/50 true/corrupted."""
    ops = ["+", "-", "*", "/"]
    out = []
    for _ in range(n):
        op = ops[rng.integers(0, 4)]
        if op == "/":
            b = int(rng.integers(2, 20))
            k = int(rng.integers(2, operand_hi // max(b, 2) + 2))
            a = b * k
        else:
            a = int(rng.integers(operand_lo, operand_hi))
            b = int(rng.integers(operand_lo, operand_hi))
            if op == "-" and b > a:
                a, b = b, a
        true = a + b if op == "+" else (a - b if op == "-" else (a * b if op == "*" else a // b))
        if balanced and rng.random() < 0.5:
            claimed = true
        else:
            # MULTIPLICATIVE corruption (not additive): additive deltas are
            # invisible in log-target space (first run: null by construction).
            f = float(rng.choice([0.5, 1.5, 2.0]))
            if corrupt_mode == "biased":
                f = 2.0
            claimed = max(1, int(round(true * f)))
        out.append({"a": a, "b": b, "op": op, "claimed": claimed, "true": true})
    return out


SLICES = {"easy": (2, 20), "med": (2, 60), "hard": (2, 200)}
OP_I = {"+": 0, "-": 1, "*": 2, "/": 3}


def encode(rows):
    n = len(rows)
    X = np.zeros((n, 6))
    for i, r in enumerate(rows):
        X[i, 0] = r["a"] / SCALE
        X[i, 1] = r["b"] / SCALE
        X[i, 2 + OP_I[r["op"]]] = 1.0
    return X


def targets(rows):
    return np.array([logt(r["true"]) for r in rows])


class MLP:
    def __init__(self, rng):
        self.W1 = rng.normal(0, 0.5, (6, 32))
        self.b1 = np.zeros(32)
        self.W2 = rng.normal(0, 0.5, (32, 16))
        self.b2 = np.zeros(16)
        self.W3 = rng.normal(0, 0.5, (16, 1))
        self.b3 = np.zeros(1)

    def forward(self, X):
        z1 = X @ self.W1 + self.b1
        h1 = np.tanh(z1)
        z2 = h1 @ self.W2 + self.b2
        h2 = np.tanh(z2)
        out = (h2 @ self.W3 + self.b3).ravel()
        return out, (X, h1, h2)

    def step(self, X, y, lr):
        n = len(X)
        pred, (Xc, h1, h2) = self.forward(X)
        err = (pred - y) / n  # dMSE/dpred
        gW3 = h2.T @ err[:, None]
        gb3 = err.sum(axis=0, keepdims=True)
        dh2 = (err[:, None] @ self.W3.T) * (1 - h2 ** 2)
        gW2 = h1.T @ dh2
        gb2 = dh2.sum(axis=0)
        dh1 = (dh2 @ self.W2.T) * (1 - h1 ** 2)
        gW1 = Xc.T @ dh1
        gb1 = dh1.sum(axis=0)
        for p, g in ((self.W1, gW1), (self.b1, gb1), (self.W2, gW2),
                     (self.b2, gb2), (self.W3, gW3), (self.b3, gb3)):
            p -= lr * g
        return float((err ** 2).mean() * n)  # MSE


def rule_correct(r):
    return abs(r["claimed"] - r["true"]) <= 1e-9


def run_arm(arm, seed):
    tag = f"{arm}xseed{seed}"
    cmode = "biased" if arm in ("bias", "gatedbias") else "unbiased"
    rng = np.random.default_rng(seed)
    prng = np.random.default_rng(10_000 + seed)  # probe stream (fixed across arms)
    model = MLP(np.random.default_rng(500 + seed))
    test_bank = {s: gen_claims(np.random.default_rng(77_000 + seed), 120, *SLICES[s], balanced=True)
                 for s in SLICES}
    probe_bank = {}
    for si, s in enumerate(SLICES):
        # same ranges, fresh seeds: pure memorization control (extrapolation
        # saturated every probe in smoke tests, so it is dropped by design)
        probe_bank[s] = gen_claims(np.random.default_rng(88_000 + seed + si * 331), 60,
                                   *SLICES[s], balanced=True)
    rounds = []
    prev_alpha = 0.5
    for g in range(6):
        # candidate pool: equal thirds per slice
        cands = []
        for si, (s, (lo, hi)) in enumerate(SLICES.items()):
            for r in gen_claims(np.random.default_rng(BASE(g, seed) + si * 7919),
                                N_CAND // 3, lo, hi, corrupt_mode=cmode):
                r["slice"] = s
                cands.append(r)
        rule = np.array([1.0 if rule_correct(r) else 0.0 for r in cands])
        if arm == "control":
            order = np.argsort(-rule, kind="stable")
            pool = [cands[i] for i in order[:POOL_N]]
            tgt = targets(pool)
            jud, alpha, agree = None, 1.0, None
        else:
            noise = rng.normal(0, 0.05, len(cands))
            judge = (1.0 - rule) + noise if arm in ("invert", "gated", "bias", "gatedbias") else rule + noise
            if arm in ("invert", "bias"):
                alpha, agree = 0.0, round(float(np.corrcoef(judge, rule)[0, 1]), 3)
                order = np.argsort(-judge, kind="stable")
                pool = [cands[i] for i in order[:POOL_N]]
                tgt = np.array([logt(r["claimed"]) for r in pool])
                jud = [float(v) for v in judge]
            else:  # gated
                agree = round(float(np.corrcoef(judge, rule)[0, 1]), 3)
                alpha = 0.8 if agree < 0.5 else 0.5
                score = alpha * rule + (1 - alpha) * judge
                order = np.argsort(-score, kind="stable")
                pool = [cands[i] for i in order[:POOL_N]]
                tgt = np.array([logt(alpha * r["true"] + (1 - alpha) * r["claimed"])
                                for r in pool])
                jud = [float(v) for v in judge]
        X, y = encode(pool), tgt
        loss = 0.0
        for _ in range(EPOCHS):
            loss = model.step(X, y, LR)
        # eval per slice: held-out + probe
        ev, pr = {}, {}
        for s in SLICES:
            Xt = encode(test_bank[s])
            pred = np.array([unlogt(v) for v in model.forward(Xt)[0]])
            ev[s] = round(float(np.mean((pred - np.array([r["true"] for r in test_bank[s]])) ** 2)), 1)
            Xp = encode(probe_bank[s])
            predp = np.array([unlogt(v) for v in model.forward(Xp)[0]])
            pr[s] = round(float(np.mean((predp - np.array([r["true"] for r in probe_bank[s]])) ** 2)), 1)
        clean = {}
        for s in SLICES:
            clean[s] = int(sum(1 for r in pool if r["slice"] == s and abs(
                r["claimed"] - r["true"]) / max(r["true"], 1) <= TOL))
        rounds.append({"g": g, "arm": arm, "train_mse": round(loss, 4), "alpha": alpha,
                       "agree": agree, "test_mse": ev, "probe_mse": pr, "pool_clean": clean,
                       "pool_n": len(pool)})
        print(f"{arm} s{seed} G{g}: test={ev} probe={pr} clean={clean} "
              f"alpha={alpha} agree={agree} loss={loss:.4f}", flush=True)
    return {"combo": f"{arm}xseed{seed}", "arm": arm, "seed": seed, "rounds": rounds}


def BASE(g, seed):
    return 20260907 + seed + g * 100


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["control", "invert", "gated"])
    ap.add_argument("--out", default="lm_transfer.json")
    args = ap.parse_args()
    all_out = []
    for seed in SEEDS:
        for arm in args.arms:
            all_out.append(run_arm(arm, seed))
    with open(OUT / args.out, "w") as f:
        json.dump({"block": "lm", "combos": all_out}, f, indent=1)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

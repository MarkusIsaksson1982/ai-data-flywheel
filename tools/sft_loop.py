"""Minimal SFT loop: pool-mass under a real updater (LoRA, CPU).

Question: does training-pool correct-mass predict capability change under SFT,
where the MLP gradient harness found r~0 (evaporation)?
Diets (matched size 36, built from pilot JSON kept sets):
  clean    : control-kept traces (mostly correct), targets = their finals
  poisoned : invert-kept traces (mostly wrong), targets = their (wrong) finals
Eval: 12-problem probe bank, generated pre/post with the (adapted) model,
parsed like the pilot (Final regex + last-integer fallback). Metric: probe
correct-rate delta overall (+ per tier, n=4, noisy — reported with caveat).
Seeds: 0/1500/3000 select pilot rounds; LoRA r=8, 2 epochs, batch 4, lr 2e-4.

Usage (venv .venv-sft):
  python tools/sft_loop.py --seed 0   # both diets; writes sft_seed0.json
"""
from __future__ import annotations
import argparse
import json
import random
import re
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
SEEDS = [0, 1500, 3000]
EPOCHS, BATCH, LR = 5, 4, 2e-4  # batch 4: ~17s/step on CPU (batch 8 thrashes to ~43s)
PROBE_TAG, PROBE_N = "Z", 10  # 30 fresh problems; eval power for ±2 effects
GEN_TOKENS = 48  # traces are short; caps eval cost

FINAL_RE = re.compile(r"Final:\s*(-?\d+)")
INT_RE = re.compile(r"-?\d+")
PROMPT_TMPL = ("Solve briefly in 1-2 steps. End with a line exactly like: Final: <number>\n"
               "Problem: {text}")


def parse_final(text):
    ms = FINAL_RE.findall(text or "")
    if ms:
        return int(ms[-1])
    ms = INT_RE.findall(text or "")
    return int(ms[-1]) if ms else None


def load_pilot_pool(seed, diet):
    """Clean/poisoned pools from pilot kept sets. Expert pool: simulator-teacher
    traces (canonical correct CoTs the model does NOT produce on its own)."""
    if diet == "expert":
        import flywheel_sim as base
        import flywheel_pkg9 as p9
        sm = base.make_sm0()
        sm.params.update({"arithmetic_acc": 0.98, "reason_depth": 2.5,
                          "format_rel": 1.0, "temperature": 0.7})
        bank = p9.make_bank(20260, 8, "W")
        rng = random.Random(6000 + seed)
        pool, k = [], 0
        while len(pool) < 36 and k < 400:
            k += 1
            prob = bank[rng.randrange(len(bank))]
            a = base.generate_artifact(sm, prob, f"EXP-{k:03d}", 0, rng)
            a["tier"] = prob["tier"]
            a.update(base.rule_evaluate(a))
            if a["correct"] and a["format_ok"]:
                pool.append(a)
        return pool
    """36 traces: control-kept (clean) or invert-kept (poisoned) across G0-G2."""
    d = json.load(open(ROOT / f"pilot_seed{seed}.json"))["combos"]
    arm = "control" if diet == "clean" else "invert"
    c = [x for x in d if x["arm"] == arm][0]
    pool = []
    for r in c["rounds"]:
        pool.extend([a for a in r["artifacts"] if a["kept"]])
    rng = random.Random(9000 + seed + (0 if diet == "clean" else 500))
    rng.shuffle(pool)
    return pool[:36]


def load_probe_problems():
    import flywheel_pkg9 as p9
    bank = p9.make_bank(5150, PROBE_N, PROBE_TAG)
    return bank


def main():
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--diet", choices=["clean", "poisoned", "expert", "both"], default="both")
    args = ap.parse_args()
    seed = args.seed

    tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"  # batch generation correctness for decoder-only models

    def chat(text):
        return tok.apply_chat_template([{"role": "user", "content": text}],
                                       tokenize=False, add_generation_prompt=True)

    def evaluate(model, tag):
        model.eval()
        tok.padding_side = "left"  # batch generation correctness for decoder-only models
        probs = load_probe_problems()
        outs = []
        t0 = time.time()
        enc = tok([chat(PROMPT_TMPL.format(text=p["text"])) for p in probs],
                  return_tensors="pt", padding=True, truncation=True, max_length=256)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=GEN_TOKENS, do_sample=False,
                                 pad_token_id=tok.eos_token_id, repetition_penalty=1.15)
        inp_len = enc["input_ids"].shape[1]
        for i, p in enumerate(probs):
            text = tok.decode(gen[i][inp_len:], skip_special_tokens=True)
            got = parse_final(text)
            outs.append({"id": p["pid"], "correct": got == p["answer"], "got": got,
                         "want": p["answer"], "text": text[:300]})
        print(f"eval {tag}: "
              f"{sum(1 for o in outs if o['correct'])}/{len(outs)} "
              f"({time.time()-t0:.0f}s)", flush=True)
        return outs

    results = {}
    base_path = ROOT / f"sft_base_seed{seed}.json"
    if base_path.exists():
        base_pre = json.load(open(base_path))["pre"]
        print(f"loaded cached base eval ({sum(1 for o in base_pre if o['correct'])}/{len(base_pre)})",
              flush=True)
    else:
        base_pre = None
    for diet in ([args.diet] if args.diet in ("clean", "poisoned", "expert") else ["clean", "poisoned"]):
        model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32,
                                                     trust_remote_code=True)
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
                                                 target_modules=["q_proj", "v_proj"],
                                                 lora_dropout=0.05, task_type="CAUSAL_LM"))
        model.train()
        if base_pre is None:
            base_pre = evaluate(model, "base-pre")
            with open(base_path, "w") as f:
                json.dump({"seed": seed, "pre": base_pre}, f)
        pre = base_pre
        pool = load_pilot_pool(seed, diet)
        n_clean = sum(1 for a in pool if a["correct"])
        print(f"diet {diet}: pool {len(pool)}, clean {n_clean}", flush=True)
        # FIX 1 (format collapse): dedupe Final lines in targets — keep the last,
        # drop earlier ones, so the model never trains on repetition.
        tok.padding_side = "right"  # positional prompt masking below needs it
        prompts, comps = [], []
        for a in pool:
            prompts.append(chat(PROMPT_TMPL.format(text=a["problem_text"])))
            lines = [l for l in list(a["cot"]) + [a["final_line"]] if l.strip()]
            finals = [l for l in lines if FINAL_RE.search(l)]
            body = [l for l in lines if not FINAL_RE.search(l)]
            comps.append("\n".join(body + finals[-1:]))
        samples = [p + c for p, c in zip(prompts, comps)]
        enc = tok(samples, return_tensors="pt", padding=True, truncation=True, max_length=256)
        # FIX 2 (diluted signal): mask prompt tokens so loss falls on answers.
        # Approximate by construction (prompt-length boundary, ±1 token) — the
        # alternative (exact span alignment) is not worth the complexity here.
        plens = [len(tok(p)["input_ids"]) for p in prompts]
        lab_full = enc["input_ids"][:, 1:].clone()
        for i, pl in enumerate(plens):
            lab_full[i, :max(0, min(pl, lab_full.shape[1]))] = -100
        lab_full[enc["attention_mask"][:, 1:] == 0] = -100
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR)
        tr = [p for p in model.parameters() if p.requires_grad]
        n_steps = (len(samples) + BATCH - 1) // BATCH * EPOCHS

        def fixed_loss():
            with torch.no_grad():
                out0 = model(input_ids=enc["input_ids"][:BATCH],
                             attention_mask=enc["attention_mask"][:BATCH])
                lg = out0.logits[:, :-1, :].contiguous()
                lb = lab_full[:BATCH].contiguous()
                lp = torch.nn.functional.cross_entropy(
                    lg.view(-1, lg.size(-1)), lb.view(-1), ignore_index=-100)
                return float(lp)
        lpre = fixed_loss()
        t0 = time.time()
        for ep in range(EPOCHS):
            idx = torch.randperm(len(samples))
            for b in range(0, len(samples), BATCH):
                bi = idx[b:b + BATCH]
                out = model(input_ids=enc["input_ids"][bi],
                            attention_mask=enc["attention_mask"][bi])
                logits = out.logits[:, :-1, :].contiguous()
                labels = lab_full[bi].contiguous()
                loss = torch.nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100)
                loss.backward()
                opt.step()
                opt.zero_grad()
        dt = time.time() - t0
        # train-loss sanity on a fixed batch (did learning happen at all?)
        lpost = fixed_loss()
        print(f"train {diet}: {n_steps} steps, {dt:.0f}s ({dt / n_steps:.1f}s/step), "
              f"fixed-batch loss {lpre:.3f} -> {lpost:.3f}", flush=True)
        post = evaluate(model, f"{diet}-post")
        d_pre = sum(1 for o in pre if o["correct"])
        d_post = sum(1 for o in post if o["correct"])
        results[diet] = {"pre": pre, "post": post, "pre_n": d_pre, "post_n": d_post,
                         "pool_clean": n_clean, "train_seconds": round(dt, 1)}
        del model
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        import gc
        gc.collect()
    with open(ROOT / f"sft_seed{seed}_{args.diet}.json", "w") as f:
        json.dump({"block": "sft", "seed": seed,
                   "combos": [{"diet": k, **{kk: v for kk, v in val.items() if kk != "pre" and kk != "post"},
                               "pre": val["pre"], "post": val["post"]} for k, val in results.items()]}, f, indent=1)
    print(f"Wrote sft_seed{seed}_{args.diet}.json")


if __name__ == "__main__":
    main()

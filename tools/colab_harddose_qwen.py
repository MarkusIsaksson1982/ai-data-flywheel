# CONSULT-2 hard-dose (Colab GPU): Qwen2.5-1.5B-Instruct (Qwen side: closes dose+device vs local-CPU ref)
# Paste this whole file into ONE Colab cell and run. Paste ALL cell output back.
# Arms: mixed = 36-trace mixed expert diet (replication anchor); hard = 36 HARD
# traces (mass+length+difficulty BUNDLED — see consult2_brief.md for scope).
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers", "peft", "accelerate", "torchao>=0.16.0"], check=True)
print("PIP DONE", flush=True)

import gc, json, random, re, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
SEEDS, EPOCHS_MID, EPOCHS_TOT, BATCH, LR = [0, 1500, 3000], 3, 5, 4, 2e-4
print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0), flush=True)
print("model:", MODEL, "| seeds:", SEEDS, "| epochs: 3->5 chained", flush=True)

W_BANK = [{"pid": "W0-00", "tier": 0, "text": "Compute 14 + 11.", "answer": 25, "steps": ["14 + 11 = 25"]}, {"pid": "W0-01", "tier": 0, "text": "A train covers 6 km, then 14 km more. Total distance?", "answer": 20, "steps": ["6 + 14 = 20"]}, {"pid": "W0-02", "tier": 0, "text": "A box contains 14 packs of 10 stickers. How many stickers?", "answer": 140, "steps": ["14 * 10 = 140"]}, {"pid": "W0-03", "tier": 0, "text": "Compute 12 * 10.", "answer": 120, "steps": ["12 * 10 = 120"]}, {"pid": "W0-04", "tier": 0, "text": "Compute 7 + 7.", "answer": 14, "steps": ["7 + 7 = 14"]}, {"pid": "W0-05", "tier": 0, "text": "A farmer has 12 apples and buys 12 more. How many in total?", "answer": 24, "steps": ["12 + 12 = 24"]}, {"pid": "W0-06", "tier": 0, "text": "A box contains 5 packs of 3 stickers. How many stickers?", "answer": 8, "steps": ["5 + 3 = 8"]}, {"pid": "W0-07", "tier": 0, "text": "Compute 2 * 14.", "answer": 28, "steps": ["2 * 14 = 28"]}, {"pid": "W1-00", "tier": 1, "text": "Compute 40 * 27 + 5.", "answer": 1085, "steps": ["40 * 27 = 1080", "1080 + 5 = 1085"]}, {"pid": "W1-01", "tier": 1, "text": "Compute 42 + 6 - 13.", "answer": 35, "steps": ["42 + 6 = 48", "48 - 13 = 35"]}, {"pid": "W1-02", "tier": 1, "text": "Compute 28 - 23 + 23.", "answer": 28, "steps": ["28 - 23 = 5", "5 + 23 = 28"]}, {"pid": "W1-03", "tier": 1, "text": "Compute 27 - 14 + 10.", "answer": 23, "steps": ["27 - 14 = 13", "13 + 10 = 23"]}, {"pid": "W1-04", "tier": 1, "text": "Compute 30 + 5 * 20.", "answer": 700, "steps": ["30 + 5 = 35", "35 * 20 = 700"]}, {"pid": "W1-05", "tier": 1, "text": "Compute 20 + 24 * 27.", "answer": 1188, "steps": ["20 + 24 = 44", "44 * 27 = 1188"]}, {"pid": "W1-06", "tier": 1, "text": "Compute 49 * 3 * 10.", "answer": 1470, "steps": ["49 * 3 = 147", "147 * 10 = 1470"]}, {"pid": "W1-07", "tier": 1, "text": "Compute 30 * 11 + 22.", "answer": 352, "steps": ["30 * 11 = 330", "330 + 22 = 352"]}, {"pid": "W2-00", "tier": 2, "text": "Compute 99 - 35 + 15 - 48.", "answer": 31, "steps": ["99 - 35 = 64", "64 + 15 = 79", "79 - 48 = 31"]}, {"pid": "W2-01", "tier": 2, "text": "Compute 6 * 13 + 20 - 50.", "answer": 48, "steps": ["6 * 13 = 78", "78 + 20 = 98", "98 - 50 = 48"]}, {"pid": "W2-02", "tier": 2, "text": "Compute 34 - 9 + 3 - 18.", "answer": 10, "steps": ["34 - 9 = 25", "25 + 3 = 28", "28 - 18 = 10"]}, {"pid": "W2-03", "tier": 2, "text": "Compute 57 * 40 * 9 - 44 - 23.", "answer": 20453, "steps": ["57 * 40 = 2280", "2280 * 9 = 20520", "20520 - 44 = 20476", "20476 - 23 = 20453"]}, {"pid": "W2-04", "tier": 2, "text": "Compute 18 + 34 + 49 - 35 + 18.", "answer": 84, "steps": ["18 + 34 = 52", "52 + 49 = 101", "101 - 35 = 66", "66 + 18 = 84"]}, {"pid": "W2-05", "tier": 2, "text": "Compute 20 * 50 + 8 + 51 + 14.", "answer": 1073, "steps": ["20 * 50 = 1000", "1000 + 8 = 1008", "1008 + 51 = 1059", "1059 + 14 = 1073"]}, {"pid": "W2-06", "tier": 2, "text": "Compute 54 + 8 + 42 * 10 + 5.", "answer": 1045, "steps": ["54 + 8 = 62", "62 + 42 = 104", "104 * 10 = 1040", "1040 + 5 = 1045"]}, {"pid": "W2-07", "tier": 2, "text": "Compute 13 + 15 + 10 + 31 + 14.", "answer": 83, "steps": ["13 + 15 = 28", "28 + 10 = 38", "38 + 31 = 69", "69 + 14 = 83"]}]
Z_PROBE = [{"pid": "Z0-00", "tier": 0, "text": "A farmer has 15 apples and buys 2 more. How many in total?", "answer": 17}, {"pid": "Z0-01", "tier": 0, "text": "Compute 10 + 4.", "answer": 14}, {"pid": "Z0-02", "tier": 0, "text": "Compute 7 + 10.", "answer": 17}, {"pid": "Z0-03", "tier": 0, "text": "A train covers 18 km, then 9 km more. Total distance?", "answer": 27}, {"pid": "Z0-04", "tier": 0, "text": "A train covers 6 km, then 7 km more. Total distance?", "answer": 13}, {"pid": "Z0-05", "tier": 0, "text": "A farmer has 13 apples and buys 18 more. How many in total?", "answer": 31}, {"pid": "Z0-06", "tier": 0, "text": "Compute 13 + 8.", "answer": 21}, {"pid": "Z0-07", "tier": 0, "text": "Compute 15 + 13.", "answer": 28}, {"pid": "Z0-08", "tier": 0, "text": "A farmer has 4 apples and buys 17 more. How many in total?", "answer": 21}, {"pid": "Z0-09", "tier": 0, "text": "Compute 12 + 14.", "answer": 26}, {"pid": "Z1-00", "tier": 1, "text": "Compute 17 * 17 * 22.", "answer": 6358}, {"pid": "Z1-01", "tier": 1, "text": "Compute 39 + 12 - 14.", "answer": 37}, {"pid": "Z1-02", "tier": 1, "text": "Compute 43 + 26 * 24.", "answer": 1656}, {"pid": "Z1-03", "tier": 1, "text": "Compute 37 * 23 - 25.", "answer": 826}, {"pid": "Z1-04", "tier": 1, "text": "Compute 21 * 18 + 8.", "answer": 386}, {"pid": "Z1-05", "tier": 1, "text": "Compute 18 * 4 + 27.", "answer": 99}, {"pid": "Z1-06", "tier": 1, "text": "Compute 39 - 8 - 27.", "answer": 4}, {"pid": "Z1-07", "tier": 1, "text": "Compute 32 + 21 + 16.", "answer": 69}, {"pid": "Z1-08", "tier": 1, "text": "Compute 15 * 6 - 7.", "answer": 83}, {"pid": "Z1-09", "tier": 1, "text": "Compute 49 + 24 + 19.", "answer": 92}, {"pid": "Z2-00", "tier": 2, "text": "Compute 51 + 27 + 43 - 9 + 12.", "answer": 124}, {"pid": "Z2-01", "tier": 2, "text": "Compute 65 * 32 + 5 + 10 - 9.", "answer": 2086}, {"pid": "Z2-02", "tier": 2, "text": "Compute 74 * 51 + 48 + 18 - 33.", "answer": 3807}, {"pid": "Z2-03", "tier": 2, "text": "Compute 53 - 5 - 47 + 10 * 48.", "answer": 528}, {"pid": "Z2-04", "tier": 2, "text": "Compute 61 + 20 + 10 + 8 * 24.", "answer": 2376}, {"pid": "Z2-05", "tier": 2, "text": "Compute 94 * 23 + 34 * 39 + 42.", "answer": 85686}, {"pid": "Z2-06", "tier": 2, "text": "Compute 42 - 35 * 19 - 16 + 4.", "answer": 121}, {"pid": "Z2-07", "tier": 2, "text": "Compute 71 * 43 + 20 + 49 * 28.", "answer": 87416}, {"pid": "Z2-08", "tier": 2, "text": "Compute 52 * 8 * 40 + 41 + 47.", "answer": 16728}, {"pid": "Z2-09", "tier": 2, "text": "Compute 60 + 20 - 31 + 28 - 16.", "answer": 61}]
HARD_BANK = [p for p in W_BANK if p["tier"] == 2]
print(f"bank: W={len(W_BANK)} hard={len(HARD_BANK)} "
      f"hard-steps={sorted(set(len(p['steps']) for p in HARD_BANK))}", flush=True)
STEP_PHRASES = ["Compute: {s}.", "Next, {s}.", "So {s}, carrying forward.",
                "Check: {s}.", "Then {s}; looks consistent."]
PROMPT_TMPL = ("Solve briefly in 1-2 steps. End with a line exactly like: Final: <number>\n"
               "Problem: {text}")
FINAL_RE = re.compile(r"Final:\s*(-?\d+)")
INT_RE = re.compile(r"-?\d+")

tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

def chat(t):
    try:
        return tok.apply_chat_template([{"role": "user", "content": t}], tokenize=False,
                                       add_generation_prompt=True)
    except Exception as e:
        print("chat-template fallback:", type(e).__name__, flush=True)
        return t

def parse_final(text):
    ms = FINAL_RE.findall(text or "")
    if ms:
        return int(ms[-1])
    ms = INT_RE.findall(text or "")
    return int(ms[-1]) if ms else None

def build_pool(bank, seed):
    rng = random.Random(6000 + seed)
    pool, k = [], 0
    while len(pool) < 36 and k < 400:
        k += 1
        p = bank[rng.randrange(len(bank))]
        cot = [rng.choice(STEP_PHRASES).format(s=s) for s in p["steps"]]
        pool.append({"problem_text": p["text"], "cot": cot,
                      "final_line": f"Final: {p['answer']}"})
    return pool

def evaluate(model, dev, tag, seed, arm):
    model.eval()
    tok.padding_side = "left"
    encq = tok([chat(PROMPT_TMPL.format(text=p["text"])) for p in Z_PROBE], return_tensors="pt",
               padding=True, truncation=True, max_length=256)
    encq = {k: v.to(dev) for k, v in encq.items()}
    with torch.no_grad():
        gen = model.generate(**encq, max_new_tokens=48, do_sample=False,
                             pad_token_id=tok.eos_token_id, repetition_penalty=1.15)
    L = encq["input_ids"].shape[1]
    tiers, fmts, accs = {}, 0, 0
    for i, p in enumerate(Z_PROBE):
        t = tok.decode(gen[i][L:].tolist(), skip_special_tokens=True)
        fmt = bool(FINAL_RE.search(t or ""))
        ok = parse_final(t) == p["answer"]
        fmts += fmt
        accs += ok
        tiers.setdefault(p["tier"], [0, 0])
        tiers[p["tier"]][0] += ok
        tiers[p["tier"]][1] += 1
    tok.padding_side = "right"
    tstr = " ".join(f"t{t}={v[0]}/{v[1]}" for t, v in sorted(tiers.items()))
    print(f"eval {tag} seed {seed} {arm}: {accs}/{len(Z_PROBE)} {tstr} "
          f"fmt={fmts}/{len(Z_PROBE)}", flush=True)
    return accs

summary = []
for SEED in SEEDS:
    for ARM, bank, off in (("mixed", W_BANK, 0), ("hard", HARD_BANK, 9000)):
        model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16,
                                                     device_map="auto", trust_remote_code=True)
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
                                                 target_modules=["q_proj", "v_proj"],
                                                 lora_dropout=0.05, task_type="CAUSAL_LM"))
        dev = str(next(model.parameters()).device)
        pool = build_pool(bank, SEED + off)
        print(f"seed {SEED} {ARM}: pool {len(pool)} traces on {dev}", flush=True)
        prompts = [chat(PROMPT_TMPL.format(text=a["problem_text"])) for a in pool]
        comps = []
        for a in pool:
            lines = [l for l in list(a["cot"]) + [a["final_line"]] if l.strip()]
            finals = [l for l in lines if FINAL_RE.search(l)]
            body = [l for l in lines if not FINAL_RE.search(l)]
            comps.append("\n".join(body + finals[-1:]))
        tok.padding_side = "right"
        enc = tok([p + c for p, c in zip(prompts, comps)], return_tensors="pt",
                  padding=True, truncation=True, max_length=256)
        enc = {k: v.to(dev) for k, v in enc.items()}
        plens = [len(tok(p)["input_ids"]) for p in prompts]
        lab = enc["input_ids"][:, 1:].clone()
        for i, pl in enumerate(plens):
            lab[i, :max(0, min(pl, lab.shape[1]))] = -100
        lab[enc["attention_mask"][:, 1:] == 0] = -100
        opt = torch.optim.AdamW([x for x in model.parameters() if x.requires_grad], lr=LR)

        def fixed_loss():
            with torch.no_grad():
                o = model(input_ids=enc["input_ids"][:BATCH],
                          attention_mask=enc["attention_mask"][:BATCH])
                lg = o.logits[:, :-1, :].contiguous()
                return float(torch.nn.functional.cross_entropy(
                    lg.view(-1, lg.size(-1)), lab[:BATCH].contiguous().view(-1),
                    ignore_index=-100))

        model.train()
        pre = evaluate(model, dev, "base-pre", SEED, ARM)
        lpre = fixed_loss()
        t0 = time.time()
        mid = None
        for ep in range(1, EPOCHS_TOT + 1):
            idx = torch.randperm(len(pool), device=dev)
            for b in range(0, len(pool), BATCH):
                bi = idx[b:b + BATCH]
                o = model(input_ids=enc["input_ids"][bi],
                          attention_mask=enc["attention_mask"][bi])
                lg = o.logits[:, :-1, :].contiguous()
                loss = torch.nn.functional.cross_entropy(
                    lg.view(-1, lg.size(-1)), lab[bi].contiguous().view(-1),
                    ignore_index=-100)
                loss.backward()
                opt.step()
                opt.zero_grad()
            if ep == EPOCHS_MID:
                mid = evaluate(model, dev, "mid-3ep", SEED, ARM)
                model.train()
        lpost = fixed_loss()
        post = evaluate(model, dev, "post-5ep", SEED, ARM)
        print(f"seed {SEED} {ARM}: {(len(pool)+BATCH-1)//BATCH*EPOCHS_TOT} steps, "
              f"{time.time()-t0:.0f}s, loss {lpre:.3f} -> {lpost:.3f}, DELTA pre={pre} "
              f"mid3={mid} post5={post}/{len(Z_PROBE)}", flush=True)
        summary.append((SEED, ARM, pre, mid, post))
        del model, opt, enc, lab
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

print(f"SUMMARY [{MODEL}] (mixed vs hard, 3ep->5ep chained):", flush=True)
for SEED, ARM, pre, mid, post in summary:
    print(f"  seed {SEED} {ARM}: {pre}->{mid}->{post}", flush=True)
print("CELL DONE", flush=True)

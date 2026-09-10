"""Emit CONSULT-2 follow-up cells (round7b, Colab pre-approved, RECOMMENDED in TUI):
  colab_ranksweep_qwen.py  — Qwen, hard arm at LoRA r8 vs r32 (adapter-capacity
                             discriminator; null t2=0 both = capacity not binding).
  colab_scaffold_tinyllama.py — TinyLlama, hard-only (replication) vs hard+scaffold
                             (30 hard + 6 easy; fmt-collapse rescue test).
One template; per-cell ARMS spec (name, r, alpha, pool-spec). Seeds [0,1500,3000],
3ep->5ep chained evals, per-tier/fmt, fresh reload per (seed, arm). Proven recipe
otherwise identical to the harddose cells.
"""
import json
from pathlib import Path

D = Path("C:/Users/mjisa/dev/flywheel")
W = json.load(open(D / "tools" / "W_bank.json"))
Z = json.load(open(D / "tools" / "Z_probe.json"))

TEMPLATE = '''# CONSULT-2 follow-up (Colab GPU): {label}
# Paste this whole file into ONE Colab cell and run. Paste ALL cell output back.
# {question}
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers", "peft", "accelerate", "torchao>=0.16.0"], check=True)
print("PIP DONE", flush=True)

import gc, json, random, re, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model

MODEL = "{model_id}"
ARMS = {arms_py}
SEEDS, EPOCHS_MID, EPOCHS_TOT, BATCH, LR = [0, 1500, 3000], 3, 5, 4, 2e-4
print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0), flush=True)
print("model:", MODEL, "| arms:", [a[0] for a in ARMS], flush=True)

W_BANK = {w_json}
Z_PROBE = {z_json}
HARD_BANK = [p for p in W_BANK if p["tier"] == 2]
EASY_BANK = [p for p in W_BANK if p["tier"] == 0]
STEP_PHRASES = ["Compute: {{s}}.", "Next, {{s}}.", "So {{s}}, carrying forward.",
                "Check: {{s}}.", "Then {{s}}; looks consistent."]
PROMPT_TMPL = ("Solve briefly in 1-2 steps. End with a line exactly like: Final: <number>\\n"
               "Problem: {{text}}")
FINAL_RE = re.compile(r"Final:\\s*(-?\\d+)")
INT_RE = re.compile(r"-?\\d+")

tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

def chat(t):
    try:
        return tok.apply_chat_template([{{"role": "user", "content": t}}], tokenize=False,
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

def draw(bank, n, seed):
    rng = random.Random(seed)
    pool, k = [], 0
    while len(pool) < n and k < 400:
        k += 1
        p = bank[rng.randrange(len(bank))]
        cot = [rng.choice(STEP_PHRASES).format(s=s) for s in p["steps"]]
        pool.append({{"problem_text": p["text"], "cot": cot,
                      "final_line": f"Final: {{p['answer']}}"}})
    return pool

def build_pool(pspec, seed):
    if pspec == "hard36":
        return draw(HARD_BANK, 36, 9000 + seed)
    if pspec == "scaffold":
        return draw(HARD_BANK, 30, 9000 + seed) + draw(EASY_BANK, 6, 9500 + seed)
    raise ValueError(pspec)

def evaluate(model, dev, tag, seed, arm):
    model.eval()
    tok.padding_side = "left"
    encq = tok([chat(PROMPT_TMPL.format(text=p["text"])) for p in Z_PROBE], return_tensors="pt",
               padding=True, truncation=True, max_length=256)
    encq = {{k: v.to(dev) for k, v in encq.items()}}
    with torch.no_grad():
        gen = model.generate(**encq, max_new_tokens=48, do_sample=False,
                             pad_token_id=tok.eos_token_id, repetition_penalty=1.15)
    L = encq["input_ids"].shape[1]
    tiers, fmts, accs = {{}}, 0, 0
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
    tstr = " ".join(f"t{{t}}={{v[0]}}/{{v[1]}}" for t, v in sorted(tiers.items()))
    print(f"eval {{tag}} seed {{seed}} {{arm}}: {{accs}}/{{len(Z_PROBE)}} {{tstr}} "
          f"fmt={{fmts}}/{{len(Z_PROBE)}}", flush=True)
    return accs

summary = []
for SEED in SEEDS:
    for ARM, RR, AA, PSPEC in ARMS:
        model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16,
                                                     device_map="auto", trust_remote_code=True)
        model = get_peft_model(model, LoraConfig(r=RR, lora_alpha=AA,
                                                 target_modules=["q_proj", "v_proj"],
                                                 lora_dropout=0.05, task_type="CAUSAL_LM"))
        dev = str(next(model.parameters()).device)
        ntr = sum(p.numel() for p in model.parameters() if p.requires_grad)
        pool = build_pool(PSPEC, SEED)
        print(f"seed {{SEED}} {{ARM}}: r={{RR}} trainable={{ntr}} pool {{len(pool)}} on {{dev}}",
              flush=True)
        prompts = [chat(PROMPT_TMPL.format(text=a["problem_text"])) for a in pool]
        comps = []
        for a in pool:
            lines = [l for l in list(a["cot"]) + [a["final_line"]] if l.strip()]
            finals = [l for l in lines if FINAL_RE.search(l)]
            body = [l for l in lines if not FINAL_RE.search(l)]
            comps.append("\\n".join(body + finals[-1:]))
        tok.padding_side = "right"
        enc = tok([p + c for p, c in zip(prompts, comps)], return_tensors="pt",
                  padding=True, truncation=True, max_length=256)
        enc = {{k: v.to(dev) for k, v in enc.items()}}
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
        print(f"seed {{SEED}} {{ARM}}: {{(len(pool)+BATCH-1)//BATCH*EPOCHS_TOT}} steps, "
              f"{{time.time()-t0:.0f}}s, loss {{lpre:.3f}} -> {{lpost:.3f}}, DELTA pre={{pre}} "
              f"mid3={{mid}} post5={{post}}/{{len(Z_PROBE)}}", flush=True)
        summary.append((SEED, ARM, pre, mid, post))
        del model, opt, enc, lab
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

print(f"SUMMARY [{{MODEL}}]:", flush=True)
for SEED, ARM, pre, mid, post in summary:
    print(f"  seed {{SEED}} {{ARM}}: {{pre}}->{{mid}}->{{post}}", flush=True)
print("CELL DONE", flush=True)
'''

CELLS = {
    "ranksweep_qwen": (
        "Qwen rank sweep: does LoRA r32 acquire t2 where r8 didn't? "
        "Null (t2=0 both) = adapter capacity not binding at this dose.",
        "Qwen/Qwen2.5-1.5B-Instruct",
        [("r8-hard", 8, 16, "hard36"), ("r32-hard", 32, 64, "hard36")]),
    "scaffold_tinyllama": (
        "TinyLlama scaffold rescue: hard-only (replication) vs 30hard+6easy. "
        "Predicts fmt holds in scaffold (vs 12->2 collapse); acc >= hard-only.",
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        [("hard-only", 8, 16, "hard36"), ("scaffold", 8, 16, "scaffold")]),
}

for name, (question, mid, arms) in CELLS.items():
    cell = TEMPLATE.format(label=question, model_id=mid, arms_py=repr(arms),
                           question=question,
                           w_json=json.dumps(W), z_json=json.dumps(Z))
    out = D / "tools" / f"colab_{name}.py"
    out.write_text(cell)
    print(f"wrote {out} ({len(cell)} chars)")

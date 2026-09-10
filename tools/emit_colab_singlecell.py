"""Emit tools/colab_singlecell_<model>.py: ONE fully self-contained Colab cell per
model (setup + frozen data + expert-diet SFT + eval). Recipe parity with the Qwen
Colab run (tools/colab_expert_cell.py): 36 canonical-correct traces, EPOCHS=3,
BATCH=4, LR=2e-4, LoRA r=8/a=16 q+v_proj, prompt-masked labels, Final-deduped
targets, Z probe x30 greedy 48 tokens rep_penalty 1.15. GPU differences only:
float16 + device_map auto (T4-safe; T4 has no bfloat16)."""
import json
from pathlib import Path

D = Path("C:/Users/mjisa/dev/flywheel")
W = json.load(open(D / "tools" / "W_bank.json"))
Z = json.load(open(D / "tools" / "Z_probe.json"))

TEMPLATE = '''# SINGLE-CELL cross-family SFT (Colab GPU): {label}
# Paste this whole file into ONE Colab cell and run. Paste ALL cell output back.
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers", "peft", "accelerate", "torchao>=0.16.0"], check=True)
print("PIP DONE", flush=True)

import json, random, re, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model

MODEL = "{model_id}"
print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0), flush=True)
print("model:", MODEL, flush=True)

# ---- frozen data (identical items to Qwen/local runs) ----
W_BANK = {w_json}
Z_PROBE = {z_json}
STEP_PHRASES = ["Compute: {{s}}.", "Next, {{s}}.", "So {{s}}, carrying forward.",
                "Check: {{s}}.", "Then {{s}}; looks consistent."]
PROMPT_TMPL = ("Solve briefly in 1-2 steps. End with a line exactly like: Final: <number>\\n"
               "Problem: {{text}}")
FINAL_RE = re.compile(r"Final:\\s*(-?\\d+)")
INT_RE = re.compile(r"-?\\d+")
EPOCHS, BATCH, LR, SEED = 3, 4, 2e-4, 0

tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16,
                                             device_map="auto", trust_remote_code=True)
model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
                                         target_modules=["q_proj", "v_proj"],
                                         lora_dropout=0.05, task_type="CAUSAL_LM"))
DEV = str(next(model.parameters()).device)
print("model on:", DEV, flush=True)

def chat(t):
    try:
        return tok.apply_chat_template([{{"role": "user", "content": t}}], tokenize=False,
                                       add_generation_prompt=True)
    except Exception as e:
        print("chat-template fallback:", type(e).__name__, flush=True)
        return t

# ---- expert pool: canonical correct traces (all correct by construction) ----
rng = random.Random(6000 + SEED)
pool, k = [], 0
while len(pool) < 36 and k < 400:
    k += 1
    p = W_BANK[rng.randrange(len(W_BANK))]
    cot = [rng.choice(STEP_PHRASES).format(s=s) for s in p["steps"]]
    pool.append({{"problem_text": p["text"], "cot": cot, "final_line": f"Final: {{p['answer']}}"}})
print(f"expert pool: {{len(pool)}} traces (all canonical-correct)", flush=True)

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
enc = {{k: v.to(DEV) for k, v in enc.items()}}
plens = [len(tok(p)["input_ids"]) for p in prompts]
lab = enc["input_ids"][:, 1:].clone()
for i, pl in enumerate(plens):
    lab[i, :max(0, min(pl, lab.shape[1]))] = -100
lab[enc["attention_mask"][:, 1:] == 0] = -100
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR)

def parse_final(text):
    ms = FINAL_RE.findall(text or "")
    if ms:
        return int(ms[-1])
    ms = INT_RE.findall(text or "")
    return int(ms[-1]) if ms else None

def evaluate(tag):
    model.eval()
    tok.padding_side = "left"
    encq = tok([chat(PROMPT_TMPL.format(text=p["text"])) for p in Z_PROBE], return_tensors="pt",
               padding=True, truncation=True, max_length=256)
    encq = {{k: v.to(DEV) for k, v in encq.items()}}
    outs = []
    with torch.no_grad():
        gen = model.generate(**encq, max_new_tokens=48, do_sample=False,
                             pad_token_id=tok.eos_token_id, repetition_penalty=1.15)
    L = encq["input_ids"].shape[1]
    for i, p in enumerate(Z_PROBE):
        t = tok.decode(gen[i][L:].tolist(), skip_special_tokens=True)
        outs.append(parse_final(t) == p["answer"])
    tok.padding_side = "right"
    acc = sum(outs)
    print(f"eval {{tag}}: {{acc}}/{{len(outs)}} = {{acc/len(outs):.3f}}", flush=True)
    return acc

def fixed_loss():
    with torch.no_grad():
        o = model(input_ids=enc["input_ids"][:BATCH], attention_mask=enc["attention_mask"][:BATCH])
        lg = o.logits[:, :-1, :].contiguous()
        return float(torch.nn.functional.cross_entropy(
            lg.view(-1, lg.size(-1)), lab[:BATCH].contiguous().view(-1), ignore_index=-100))

model.train()
pre = evaluate("base-pre")
lpre = fixed_loss()
t0 = time.time()
n_steps = (len(pool) + BATCH - 1) // BATCH * EPOCHS
for ep in range(EPOCHS):
    idx = torch.randperm(len(pool), device=DEV)
    for b in range(0, len(pool), BATCH):
        bi = idx[b:b + BATCH]
        o = model(input_ids=enc["input_ids"][bi], attention_mask=enc["attention_mask"][bi])
        lg = o.logits[:, :-1, :].contiguous()
        loss = torch.nn.functional.cross_entropy(
            lg.view(-1, lg.size(-1)), lab[bi].contiguous().view(-1), ignore_index=-100)
        loss.backward()
        opt.step()
        opt.zero_grad()
print(f"train: {{n_steps}} steps, {{time.time()-t0:.0f}}s, fixed-batch loss {{lpre:.3f}} -> {{fixed_loss():.3f}}",
      flush=True)
post = evaluate("expert-post")
print(f"DELTA [{{MODEL}}]: pre={{pre}}/30 post={{post}}/30", flush=True)
print("CELL DONE", flush=True)
'''

MODELS = {
    "qwen": ("Qwen2.5-1.5B-Instruct (Qwen side: closes dose+device vs local-CPU ref)",
             "Qwen/Qwen2.5-1.5B-Instruct"),
    "smollm2": ("SmolLM2-1.7B-Instruct (primary: non-Qwen family, T4-fits)",
                "HuggingFaceTB/SmolLM2-1.7B-Instruct"),
    "tinyllama": ("TinyLlama-1.1B-Chat (parallel: Llama-arch family, lightest)",
                  "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
}

for name, (label, mid) in MODELS.items():
    cell = TEMPLATE.format(label=label, model_id=mid,
                           w_json=json.dumps(W), z_json=json.dumps(Z))
    out = D / "tools" / f"colab_singlecell_{name}.py"
    out.write_text(cell)
    print(f"wrote {out} ({len(cell)} chars)")

# ---------------------------------------------------------------------------
# Batched variant: seeds 1500+3000 in ONE run + per-tier/format instrumentation.
# EPOCHS=5 for every model (all three gain more at 5 than at 3: Qwen +5/+1,
# SmolLM2 +5/+4, TinyLlama +11/+7). Model reloaded fresh per seed so adapters
# never compound across seeds.
# ---------------------------------------------------------------------------
BTEMPLATE = '''# BATCHED seeds 1500+3000 + per-tier/format instrumentation (Colab GPU): {label}
# Paste this whole file into ONE Colab cell and run. Paste ALL cell output back.
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers", "peft", "accelerate", "torchao>=0.16.0"], check=True)
print("PIP DONE", flush=True)

import gc, json, random, re, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model

MODEL = "{model_id}"
SEEDS, EPOCHS, BATCH, LR = [1500, 3000], 5, 4, 2e-4
print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0), flush=True)
print("model:", MODEL, "| seeds:", SEEDS, "| epochs:", EPOCHS, flush=True)

W_BANK = {w_json}
Z_PROBE = {z_json}
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

def evaluate(model, dev, tag, seed):
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
    print(f"eval {{tag}} seed {{seed}}: {{accs}}/{{len(Z_PROBE)}} {{tstr}} fmt={{fmts}}/{{len(Z_PROBE)}}",
          flush=True)
    return accs, tiers, fmts

summary = []
for SEED in SEEDS:
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16,
                                                 device_map="auto", trust_remote_code=True)
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
                                             target_modules=["q_proj", "v_proj"],
                                             lora_dropout=0.05, task_type="CAUSAL_LM"))
    dev = str(next(model.parameters()).device)
    rng = random.Random(6000 + SEED)
    pool, k = [], 0
    while len(pool) < 36 and k < 400:
        k += 1
        p = W_BANK[rng.randrange(len(W_BANK))]
        cot = [rng.choice(STEP_PHRASES).format(s=s) for s in p["steps"]]
        pool.append({{"problem_text": p["text"], "cot": cot,
                      "final_line": f"Final: {{p['answer']}}"}})
    print(f"seed {{SEED}}: expert pool {{len(pool)}} traces on {{dev}}", flush=True)
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
                lg.view(-1, lg.size(-1)), lab[:BATCH].contiguous().view(-1), ignore_index=-100))

    model.train()
    pre, pret, prefmt = evaluate(model, dev, "base-pre", SEED)
    lpre = fixed_loss()
    t0 = time.time()
    n_steps = (len(pool) + BATCH - 1) // BATCH * EPOCHS
    for ep in range(EPOCHS):
        idx = torch.randperm(len(pool), device=dev)
        for b in range(0, len(pool), BATCH):
            bi = idx[b:b + BATCH]
            o = model(input_ids=enc["input_ids"][bi], attention_mask=enc["attention_mask"][bi])
            lg = o.logits[:, :-1, :].contiguous()
            loss = torch.nn.functional.cross_entropy(
                lg.view(-1, lg.size(-1)), lab[bi].contiguous().view(-1), ignore_index=-100)
            loss.backward()
            opt.step()
            opt.zero_grad()
    lpost = fixed_loss()
    post, postt, postfmt = evaluate(model, dev, "expert-post", SEED)
    print(f"seed {{SEED}}: {{n_steps}} steps, {{time.time()-t0:.0f}}s, loss {{lpre:.3f}} -> {{lpost:.3f}}, "
          f"DELTA pre={{pre}}/{{len(Z_PROBE)}} post={{post}}/{{len(Z_PROBE)}}", flush=True)
    summary.append((SEED, pre, post, pret, postt, prefmt, postfmt))
    del model, opt, enc, lab
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

print(f"SUMMARY [{{MODEL}}] (epochs={{EPOCHS}}):", flush=True)
for SEED, pre, post, pret, postt, prefmt, postfmt in summary:
    d = " ".join(f"t{{t}}:{{pret[t][0]}}/{{pret[t][1]}}->{{postt[t][0]}}/{{postt[t][1]}}"
                 for t in sorted(pret))
    print(f"  seed {{SEED}}: {{pre}}->{{post}} | {{d}} | fmt {{prefmt}}->{{postfmt}}", flush=True)
print("CELL DONE", flush=True)
'''

for name, (label, mid) in MODELS.items():
    cell = BTEMPLATE.format(label=label, model_id=mid,
                            w_json=json.dumps(W), z_json=json.dumps(Z))
    out = D / "tools" / f"colab_batch_{name}.py"
    out.write_text(cell)
    print(f"wrote {out} ({len(cell)} chars)")

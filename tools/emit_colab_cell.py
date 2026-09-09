"""Emit tools/colab_expert_cell.py: ONE self-contained Colab cell for the expert-diet
SFT run (assumes the setup cell already created tok + LoRA model)."""
import json
from pathlib import Path

D = Path("C:/Users/mjisa/dev/flywheel")
W = json.load(open(D / "tools" / "W_bank.json"))
Z = json.load(open(D / "tools" / "Z_probe.json"))

cell = '''# CELL: expert-diet SFT (single cell; setup cell must have run: tok + LoRA model)
import json, random, re, time
import torch

# ---- frozen data (identical items to local runs) ----
W_BANK = %s
Z_PROBE = %s
STEP_PHRASES = ["Compute: {s}.", "Next, {s}.", "So {s}, carrying forward.",
                "Check: {s}.", "Then {s}; looks consistent."]
PROMPT_TMPL = ("Solve briefly in 1-2 steps. End with a line exactly like: Final: <number>\\n"
               "Problem: {text}")
FINAL_RE = re.compile(r"Final:\\s*(-?\\d+)")
INT_RE = re.compile(r"-?\\d+")
EPOCHS, BATCH, LR, SEED = 3, 4, 2e-4, 0
if "model" not in dir() or "tok" not in dir():
    raise SystemExit("run the setup cell first (needs tok + LoRA model)")
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
tok.padding_side = "right"
DEV = str(next(model.parameters()).device)  # cuda on Colab, cpu locally

# ---- expert pool: canonical correct traces (all correct by construction) ----
rng = random.Random(6000 + SEED)
pool, k = [], 0
order = list(range(len(W_BANK)))
while len(pool) < 36 and k < 400:
    k += 1
    p = W_BANK[rng.randrange(len(W_BANK))]
    cot = [rng.choice(STEP_PHRASES).format(s=s) for s in p["steps"]]
    pool.append({"problem_text": p["text"], "cot": cot, "final_line": f"Final: {p['answer']}"})
print(f"expert pool: {len(pool)} traces (all canonical-correct)")

# ---- targets: Final-dedupe + prompt-masked labels (same recipe as local) ----
def chat(t):
    return tok.apply_chat_template([{"role": "user", "content": t}], tokenize=False,
                                   add_generation_prompt=True)
prompts = [chat(PROMPT_TMPL.format(text=a["problem_text"])) for a in pool]
comps = []
for a in pool:
    lines = [l for l in list(a["cot"]) + [a["final_line"]] if l.strip()]
    finals = [l for l in lines if FINAL_RE.search(l)]
    body = [l for l in lines if not FINAL_RE.search(l)]
    comps.append("\\n".join(body + finals[-1:]))
enc = tok([p + c for p, c in zip(prompts, comps)], return_tensors="pt",
          padding=True, truncation=True, max_length=256)
enc = {k: v.to(DEV) for k, v in enc.items()}
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
    encq = {k: v.to(DEV) for k, v in encq.items()}
    outs = []
    with torch.no_grad():
        gen = model.generate(**encq, max_new_tokens=48, do_sample=False,
                             pad_token_id=tok.eos_token_id, repetition_penalty=1.15)
    L = encq["input_ids"].shape[1]
    for i, p in enumerate(Z_PROBE):
        t = tok.decode(gen[i][L:].tolist(), skip_special_tokens=True)
        got = parse_final(t)
        outs.append(got == p["answer"])
    tok.padding_side = "right"
    acc = sum(outs)
    print(f"eval {tag}: {acc}/{len(outs)} = {acc/len(outs):.3f}", flush=True)
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
print(f"train: {n_steps} steps, {time.time()-t0:.0f}s, fixed-batch loss {lpre:.3f} -> {fixed_loss():.3f}",
      flush=True)
post = evaluate("expert-post")
print(f"DELTA: pre={pre}/30 post={post}/30 (local CPU reference: 15->9 seed0, 15->7 seed1500)")
print("CELL DONE")
''' % (json.dumps(W), json.dumps(Z))
out = D / "tools" / "colab_expert_cell.py"
out.write_text(cell)
print(f"wrote {out} ({len(cell)} chars)")

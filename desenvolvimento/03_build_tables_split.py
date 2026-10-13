# ═══════════════════════════════════════════════════════════════════
# 03 — TABELAS + SPLIT
# ═══════════════════════════════════════════════════════════════════
import json, hashlib
from pathlib import Path
from collections import Counter, defaultdict

PIPE = Path("/content/drive/MyDrive/fonetizador/pipeline")
UNIFIED = PIPE / "unified_stanza.jsonl"
V3 = PIPE / "v3"
V3.mkdir(exist_ok=True, parents=True)

TABELAS = V3 / "tabelas_v3.json"
STATS   = V3 / "stats_v3.json"
TRAIN   = V3 / "train.jsonl"
VAL     = V3 / "val.jsonl"
TEST    = V3 / "test.jsonl"

ALL_POS = ["NOUN","PROPN","VERB","AUX","ADJ","ADV","PRON","DET",
           "ADP","CCONJ","SCONJ","NUM","PART","INTJ","PUNCT","SYM","X"]

MIN_ALWAYS = 10
MIN_NEVER  = 10
MIN_AMBIG  = 5
PRUNE_REL  = 0.02
PRUNE_ABS  = 3

def split_of(text):
    h = int(hashlib.md5(text.encode()).hexdigest()[:8], 16) % 100
    if h < 90: return "train"
    if h < 95: return "val"
    return "test"

# ─── 1. Contagens ─────────────────────────────────────────────────
print("[1] Contagens...", flush=True)
counts = defaultdict(Counter)
n_sent = n_tok = 0

with open(UNIFIED, encoding="utf-8") as f:
    for line in f:
        try: r = json.loads(line)
        except: continue
        n_sent += 1
        for t in r.get("tokens", []):
            txt = (t.get("text") or "").lower()
            upos = t.get("upos") or ""
            if not txt or not upos: continue
            n_tok += 1
            counts[txt][upos] += 1

print(f"  frases={n_sent:,} tokens={n_tok:,} tipos={len(counts):,}")

# ─── 2. Poda de ruído ─────────────────────────────────────────────
print("[2] Poda...", flush=True)
def podar(c):
    tot = sum(c.values())
    out = Counter()
    for p, n in c.items():
        if n >= PRUNE_ABS and n / tot >= PRUNE_REL:
            out[p] = n
    if not out and c:
        out[c.most_common(1)[0][0]] = c.most_common(1)[0][1]
    return out

counts_limpos = {w: podar(c) for w, c in counts.items()}

# ─── 3. Tabelas ───────────────────────────────────────────────────
print("[3] Tabelas...", flush=True)
always = defaultdict(set)
never  = defaultdict(set)
prior  = {}
ambig  = {}
total  = {}

for w, c in counts_limpos.items():
    tot = sum(c.values())
    if tot == 0: continue
    total[w] = tot
    poss = set(c)
    prior[w] = {p: c[p] / tot for p in poss}
    if tot >= MIN_ALWAYS and len(poss) == 1:
        always[next(iter(poss))].add(w)
    if tot >= MIN_NEVER:
        for p in ALL_POS:
            if p not in poss: never[p].add(w)
    if tot >= MIN_AMBIG and len(poss) > 1:
        ambig[w] = poss

print("  always: " + " ".join(f"{p}={len(always[p]):,}" for p in ALL_POS if always[p]))
print("  never:  " + " ".join(f"{p}={len(never[p]):,}"  for p in ALL_POS if never[p]))
print(f"  ambig:  {len(ambig):,}")

# ─── 4. Split ─────────────────────────────────────────────────────
print("[4] Split...", flush=True)
fout = {k: open(V3/f"{k}.jsonl", "w", encoding="utf-8")
        for k in ("train","val","test")}
nsp = Counter()

with open(UNIFIED, encoding="utf-8") as f:
    for line in f:
        try: r = json.loads(line)
        except: continue
        s = split_of(r["text"])
        fout[s].write(line)
        nsp[s] += 1

for f in fout.values(): f.close()
print(f"  {dict(nsp)}")

# ─── 5. Salva ─────────────────────────────────────────────────────
print("[5] Salvando...", flush=True)
TABELAS.write_text(json.dumps({
    "meta": {
        "n_sent": n_sent, "n_tok": n_tok, "n_tipos": len(counts_limpos),
        "min_always": MIN_ALWAYS, "min_never": MIN_NEVER,
        "min_ambig": MIN_AMBIG, "prune_rel": PRUNE_REL, "prune_abs": PRUNE_ABS,
    },
    "always": {p: sorted(always[p]) for p in ALL_POS},
    "never":  {p: sorted(never[p])  for p in ALL_POS},
    "prior":  {w: {p: round(v, 6) for p, v in pr.items()}
               for w, pr in prior.items() if total[w] >= 3},
    "ambig":  {w: sorted(poss) for w, poss in ambig.items()},
}, ensure_ascii=False), encoding="utf-8")

STATS.write_text(json.dumps({
    "frases": n_sent, "tokens": n_tok, "splits": dict(nsp),
    "always": {p: len(always[p]) for p in ALL_POS},
    "never":  {p: len(never[p])  for p in ALL_POS},
    "n_ambig": len(ambig),
}, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"  ✓ {TABELAS}")
print(f"  ✓ {STATS}")
print(f"  ✓ {TRAIN}, {VAL}, {TEST}")

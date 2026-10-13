# ═══════════════════════════════════════════════════════════════════
# 06 — TREINO DO RESOLVER DE DIACRÍTICOS
# ═══════════════════════════════════════════════════════════════════
import json, unicodedata as ud, time
from pathlib import Path
from collections import Counter, defaultdict

PIPE    = Path("/content/drive/MyDrive/fonetizador/pipeline")
V3      = PIPE / "v3"
UNIFIED = PIPE / "unified_stanza.jsonl"
DIAC    = PIPE / "v9_11" / "diacriticos_table.json"
OUT     = V3 / "resolver_v7.json"

ALL_POS = ["NOUN","PROPN","VERB","AUX","ADJ","ADV","PRON","DET",
           "ADP","CCONJ","SCONJ","NUM","PART","INTJ","PUNCT","SYM","X"]
ID = {p:i for i,p in enumerate(ALL_POS)}
NONE = -1

def sem_acento(s):
    return "".join(c for c in ud.normalize("NFKD", s) if not ud.combining(c))

def log(*a): print(*a, flush=True)

DIAC_TABLE = json.loads(DIAC.read_text(encoding="utf-8"))
ALVOS = {w.lower() for w in DIAC_TABLE}
log(f"[load] alvos: {len(ALVOS)}")

L_full  = defaultdict(lambda: defaultdict(Counter))
L_pw    = defaultdict(lambda: defaultdict(Counter))
L_prev  = defaultdict(lambda: defaultdict(Counter))
L_next  = defaultdict(lambda: defaultdict(Counter))
L_cls   = defaultdict(lambda: defaultdict(Counter))
L_upos  = defaultdict(lambda: defaultdict(Counter))
L_prior = defaultdict(Counter)

n_proc = n_ok = n_skip = 0
t0 = time.time()

with open(UNIFIED, encoding="utf-8") as f:
    for line in f:
        try: r = json.loads(line)
        except: continue
        toks = r.get("tokens") or []
        senses = r.get("senses") or []
        if not toks or not senses: continue
        n_proc += 1

        words  = [(t.get("text") or "").lower() for t in toks]
        cleans = [sem_acento(w) for w in words]
        upos   = [ID.get(t.get("upos") or "X", NONE) for t in toks]

        for a in senses:
            idx = a.get("idx")
            w_a = (a.get("w") or "").lower()
            sense = (a.get("sense") or "").lower()
            if idx is None or not w_a or not sense: continue
            wc = sem_acento(w_a)
            if wc not in ALVOS: continue
            diac = DIAC_TABLE.get(wc, {}).get(sense)
            if not diac: continue
            diac = diac.lower()

            j = None
            for k in range(max(0, idx-2), min(len(toks), idx+3)):
                if cleans[k] == wc:
                    j = k; break
            if j is None: n_skip += 1; continue

            prev_w  = words[j-1]  if j > 0 else ""
            next_w  = words[j+1]  if j+1 < len(toks) else ""
            prev2_w = words[j-2]  if j > 1 else ""
            next2_w = words[j+2]  if j+2 < len(toks) else ""
            prev_u  = upos[j-1] if j > 0 else NONE
            next_u  = upos[j+1] if j+1 < len(toks) else NONE
            u       = upos[j]

            L_full[wc][(u, prev_w, next_w, prev_u, next_u, prev2_w, next2_w)][diac] += 1
            L_pw[wc][(u, prev_w, next_w)][diac] += 1
            L_prev[wc][(u, prev_w)][diac] += 1
            L_next[wc][(u, next_w)][diac] += 1
            L_cls[wc][(u, prev_u, next_u)][diac] += 1
            L_upos[wc][(u,)][diac] += 1
            L_prior[wc][diac] += 1
            n_ok += 1

        if n_proc % 200_000 == 0:
            log(f"  {n_proc:,} frases  {n_ok:,} exemplos")

log(f"[ok] {n_proc:,} frases  {n_ok:,} exemplos  {n_skip:,} pulados")

MIN = {"full": 3, "pw": 3, "prev": 2, "next": 2, "cls": 3, "upos": 2}
def ks(tup): return "|".join(str(x) for x in tup)

resolver = {}
for w in L_full:
    niveis = {}
    for nome, tabela, minc in [
        ("full", L_full, MIN["full"]), ("pw", L_pw, MIN["pw"]),
        ("prev", L_prev, MIN["prev"]), ("next", L_next, MIN["next"]),
        ("cls", L_cls, MIN["cls"]),   ("upos", L_upos, MIN["upos"]),
    ]:
        t = {}
        for k, c in tabela[w].items():
            if sum(c.values()) >= minc:
                t[ks(k)] = c.most_common(1)[0][0]
        if t: niveis[nome] = t
    if niveis: resolver[w] = niveis

prior = {w: c.most_common(1)[0][0] for w, c in L_prior.items()}

OUT.write_text(json.dumps({"resolver": resolver, "prior": prior},
                          ensure_ascii=False), encoding="utf-8")
log(f"[ok] {OUT}")
log(f"  palavras com resolver: {len(resolver):,}")
log(f"  prior: {len(prior):,}")

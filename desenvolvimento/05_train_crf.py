# ═══════════════════════════════════════════════════════════════════
# 05 — TREINO DO CRF + EXPORT
# ═══════════════════════════════════════════════════════════════════
import json, pickle, time
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
import sklearn_crfsuite

V3      = Path("/content/drive/MyDrive/fonetizador/pipeline/v3")
MODS    = V3 / "models"
FEAT_V2 = V3 / "features_v2"

MAX_TRAIN_SENTS = 1_500_000
C1, C2          = 0.1, 0.1
MAX_ITER        = 150
RANDOM_SEED     = 42

ALL_POS = ["NOUN","PROPN","VERB","AUX","ADJ","ADV","PRON","DET",
           "ADP","CCONJ","SCONJ","NUM","PART","INTJ","PUNCT","SYM","X"]
ID = {p:i for i,p in enumerate(ALL_POS)}
def log(*a): print(*a, flush=True)

log("[1] Carregando train.parquet...")
df = pd.read_parquet(FEAT_V2 / "train.parquet")
n_sids = df["sent_id"].nunique()
log(f"  shape={df.shape}  sents={n_sids:,}")

if MAX_TRAIN_SENTS and n_sids > MAX_TRAIN_SENTS:
    rng = np.random.RandomState(RANDOM_SEED)
    sids = rng.choice(n_sids, size=MAX_TRAIN_SENTS, replace=False)
    sub = df[df["sent_id"].isin(set(sids.tolist()))].copy()
else:
    sub = df.copy()
sub = sub.sort_values("sent_id", kind="stable")
log(f"  subset={sub.shape}  sents={sub['sent_id'].nunique():,}")
del df

def row_to_feats(row):
    w = row.word
    f = {}
    f["w=" + w] = 1.0
    f["s3=" + w[-3:]] = 1.0
    f["s2=" + w[-2:]] = 1.0
    f["s1=" + w[-1:]] = 1.0
    f["p1=" + row.prev1_w] = 1.0
    f["n1=" + row.next1_w] = 1.0
    f["p2=" + row.prev2_w] = 1.0
    f["n2=" + row.next2_w] = 1.0
    f["len=" + str(int(row.len))] = 1.0
    f["cap=" + str(int(row.cap))] = 1.0
    f["pa=" + str(int(row.prior_argmax))] = 1.0
    f["pmax=" + str(min(int(row.prior_max * 10), 10))] = 1.0
    f["cp1=" + str(int(row.c_prev1))] = 1.0
    f["cp2=" + str(int(row.c_prev2))] = 1.0
    f["cp3=" + str(int(row.c_prev3))] = 1.0
    f["cn1=" + str(int(row.c_next1))] = 1.0
    f["cn2=" + str(int(row.c_next2))] = 1.0
    f["cn3=" + str(int(row.c_next3))] = 1.0
    f["lap=" + str(int(row.left_anchor_pos))] = 1.0
    f["lad=" + str(int(row.left_anchor_dist))] = 1.0
    f["rap=" + str(int(row.right_anchor_pos))] = 1.0
    f["rad=" + str(int(row.right_anchor_dist))] = 1.0
    f["nal=" + str(int(row.n_anchors_left))] = 1.0
    f["nar=" + str(int(row.n_anchors_right))] = 1.0
    f["ifl=" + str(int(row.is_first))] = 1.0
    f["isl=" + str(int(row.is_last))] = 1.0
    f["dpl=" + str(int(row.dist_punct_left))] = 1.0
    f["dpr=" + str(int(row.dist_punct_right))] = 1.0
    f["cm=" + str(int(row.cands_mask))] = 1.0
    f["w|cp1=" + w + "|" + str(int(row.c_prev1))] = 1.0
    f["w|cn1=" + w + "|" + str(int(row.c_next1))] = 1.0
    f["w|cm=" + w + "|" + str(int(row.cands_mask))] = 1.0
    f["cp1|cn1=" + str(int(row.c_prev1)) + "|" + str(int(row.c_next1))] = 1.0
    f["s2|cp1=" + w[-2:] + "|" + str(int(row.c_prev1))] = 1.0
    f["s2|cn1=" + w[-2:] + "|" + str(int(row.c_next1))] = 1.0
    f["pa|cp1=" + str(int(row.prior_argmax)) + "|" + str(int(row.c_prev1))] = 1.0
    return f

log("[2] Construindo sequências...")
t0 = time.time()
X_seq, y_seq = [], []
cur = None; cx, cy = [], []
for row in sub.itertuples(index=False):
    if row.sent_id != cur:
        if cx: X_seq.append(cx); y_seq.append(cy)
        cx, cy = [], []; cur = row.sent_id
    cx.append(row_to_feats(row))
    cy.append(ALL_POS[int(row.target)])
if cx: X_seq.append(cx); y_seq.append(cy)
log(f"  {len(X_seq):,} seqs em {time.time()-t0:.1f}s")
del sub

log(f"[3] Treinando (c1={C1}, c2={C2}, iter={MAX_ITER})")
crf = sklearn_crfsuite.CRF(
    algorithm="lbfgs", c1=C1, c2=C2,
    max_iterations=MAX_ITER,
    all_possible_transitions=True, verbose=False)
t0 = time.time(); crf.fit(X_seq, y_seq)
log(f"  treino em {time.time()-t0:.1f}s")

MODS.mkdir(exist_ok=True)
CRF_PATH = MODS / "crf_final.pkl"
with open(CRF_PATH, "wb") as f: pickle.dump(crf, f)
log(f"  ✓ {CRF_PATH}")
del X_seq, y_seq

log("[4] Avaliando no val...")
df_va = pd.read_parquet(FEAT_V2 / "val.parquet").sort_values("sent_id", kind="stable")
X_va, y_va = [], []
cur = None; cx, cy = [], []
for row in df_va.itertuples(index=False):
    if row.sent_id != cur:
        if cx: X_va.append(cx); y_va.append(cy)
        cx, cy = [], []; cur = row.sent_id
    cx.append(row_to_feats(row))
    cy.append(ALL_POS[int(row.target)])
if cx: X_va.append(cx); y_va.append(cy)

y_pred = crf.predict(X_va)
flat_y = [t for s in y_va for t in s]
flat_p = [t for s in y_pred for t in s]
acc = sum(1 for a,b in zip(flat_y, flat_p) if a == b) / len(flat_y)
log(f"  POS acc (val): {acc*100:.4f}%")

log("[5] Exportando pesos...")
labels = list(crf.classes_)
n = len(labels)
lab_idx = {l: i for i, l in enumerate(labels)}
state = defaultdict(list)
for (attr, label), w in crf.state_features_.items():
    state[attr].append([lab_idx[label], float(w)])
trans = [[0.0] * n for _ in range(n)]
for (f_l, t_l), w in crf.transition_features_.items():
    trans[lab_idx[f_l]][lab_idx[t_l]] = float(w)

WEIGHTS_PATH = MODS / "crf_weights.json"
WEIGHTS_PATH.write_text(json.dumps({
    "labels": labels, "state": dict(state), "trans": trans,
}, ensure_ascii=False), encoding="utf-8")
log(f"  ✓ {WEIGHTS_PATH}  ({WEIGHTS_PATH.stat().st_size/1e6:.1f} MB)")

log(f"\n✓ DONE  POS acc: {acc*100:.4f}%")

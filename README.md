<div align="center">

<img src="BCDE.png" alt="BCDE-tagger" width="400"/>

# BCDE-tagger

**POS tagging e desambiguação de homógrafos para português brasileiro.**

Tagger rápido, determinístico e sem dependências neurais — CRF linear + tabelas + resolver de diacríticos.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.75%2B-orange.svg)](https://www.rust-lang.org)
[![Accuracy POS](https://img.shields.io/badge/POS-98.72%25-success.svg)]()
[![Accuracy Diacríticos](https://img.shields.io/badge/diacr%C3%ADticos-98.01%25-success.svg)]()
[![Throughput](https://img.shields.io/badge/throughput-9.7k%20frases%2Fs-blueviolet.svg)]()

</div>

---

## Sumário

- [Sobre](#sobre)
- [Por que existe](#por-que-existe)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Instalação](#instalação)
- [Uso](#uso)
- [Formato de saída](#formato-de-saída)
- [Acurácia](#acurácia)
- [Benchmarks](#benchmarks)
- [Tokenização](#tokenização)
- [Desambiguação de homógrafos](#desambiguação-de-homógrafos)
- [Datasets e fontes](#datasets-e-fontes)
- [Limitações](#limitações)
- [Licença](#licença)
- [Citação](#citação)
- [Agradecimentos](#agradecimentos)

---

## Sobre

O `BCDE-tagger` é um **POS-tagger rápido e leve** para português brasileiro, com desambiguação de homógrafos e diacríticos. Zero dependências neurais em produção.

Roda em:

- **Rust** — binário de ~2.3 MB, single-thread, sem runtime externo
- **Python** — via binding sobre o binário

O tagger é uma **destilação de conhecimento** de modelos como o Stanza e a biblioteca [Bifonia](https://github.com/TigreGotico/bifonia) do Tigre Gotico. Ele combina:

- **CRF linear** treinado em ~1.5M sentenças anotadas
- **Tabelas determinísticas** para casos de cobertura total
- **Resolver de diacríticos** por backoff hierárquico de 7 níveis

O resultado é um tagger que roda a **~9.700 frases/s** em single-thread, com **98.72% de acurácia POS** e **98.01% de acurácia em diacríticos**.

---

## Por que existe

O projeto nasceu da necessidade de um POS-tagger para TTS (text-to-speech) em português brasileiro, que fosse:

- **Rápido** o suficiente para rodar em tempo real sem GPU
- **Pequeno** o suficiente para embarcar em binários de aplicações
- **Preciso** o suficiente para desambiguar homógrafos como `sede` (seat/thirst), `forma` (shape/mould), `molho` (sauce/bundle) e manter a naturalidade do áudio

A biblioteca [Bifonia](https://github.com/TigreGotico/bifonia) provou que POS tagging sozinho não resolve homógrafos que compartilham a mesma classe gramatical. O `BCDE-tagger` foi construído para resolver esse problema com contexto rico e desambiguação por sentidos — mas de forma simplificada.

---

## Funcionalidades

| Função | Descrição |
|--------|-----------|
| `tag(text)` | Lista de tokens com POS, diacrítico e sentido |
| `tag_batch(texts)` | Processa lista de textos em paralelo |
| POS tagging | 17 classes Universal Dependencies |
| MWT expansion | 80 contrações expandidas automaticamente |
| Diacrítico | 131 homógrafos desambiguados por contexto |
| Sentido | Label semântico (`seat`, `thirst`, `hair`, etc.) |
| CLI | `echo "frase" \| ./bcde-tagger data` |
| Biblioteca Rust | Crate importável |
| Binding Python | Via subprocess ou reimplementação |

---

## Arquitetura

```
texto cru
    │
    ▼
[tokenizer.rs]              regex + expansão MWT
    │
    ▼
[tabelas always/never/prior]   ← 56.7% dos tokens resolvidos aqui
    │
    ▼
[extração de features]          ← 45 features por token ambíguo
    │
    ▼
[crf.rs] Viterbi                ← 41.8% dos tokens ambíguos
    │
    ▼
[resolver.rs] backoff 7 níveis  ← diacríticos para homógrafos
    │
    ▼
saída: POS + diacrítico + sentido
```

**Cobertura:** 56.7% dos tokens são resolvidos por consulta direta a tabelas (zero custo). 41.8% passam pelo CRF. 1.5% caem em regras genéricas.

---

## Estrutura do repositório

```
BCDE-tagger/
├── Cargo.toml                    # deps: regex, serde, once_cell
├── LICENSE                       # MIT
├── README.md
├── data/
│   ├── tabelas_v3.json           # always/never/prior/ambig (40 MB)
│   ├── crf_weights.json          # pesos do CRF (62 MB)
│   ├── resolver_v7.json          # resolver de diacríticos (5 MB)
│   └── diacriticos_table.json    # 131 homógrafos → sentido (50 KB)
├── python/
│   └── tagger_python.py          # binding Python via subprocess
└── src/
    ├── main.rs                   # CLI: lê stdin, escreve stdout
    ├── tagger.rs                 # orquestração + extração de features
    ├── tokenizer.rs              # regex + expansão MWT
    ├── crf.rs                    # Viterbi
    └── resolver.rs               # backoff de diacríticos
```

---

## Instalação

### Rust (recomendado)

```bash
git clone https://github.com/bcdeosce/BCDE-tagger
cd BCDE-tagger
cargo build --release
```

O binário fica em `target/release/bcde-tagger` (~2.3 MB).

### Python

```bash
# Compile o binário Rust primeiro
cargo build --release

# Use via subprocess
python python/tagger_python.py "A sede da empresa é grande."
```

### Dependências

**Rust:**

- `regex` — tokenização
- `serde` + `serde_json` — desserialização dos JSONs
- `once_cell` — lazy statics

Nenhuma dependência neural. Nenhum runtime C++. Nenhuma GPU.

---

## Uso

### CLI

```bash
echo "A sede da empresa é grande." | ./target/release/bcde-tagger data
```

Saída:

```
A       DET
sede    NOUN    diac=séde      sense=seat     via=pw
de      ADP
a       DET
empresa NOUN
é       AUX
grande  ADJ
.       PUNCT
```

### Biblioteca Rust

### Biblioteca Rust

Adicione ao `Cargo.toml` do seu projeto:

```toml
[dependencies]
bcde-tagger = { git = "https://github.com/bcdeosce/BCDE-tagger" }
```

Ou, se o crate estiver publicado no crates.io:

```toml
[dependencies]
bcde-tagger = "0.1.0"
```

Código:

```rust
use bcde_tagger::Tagger;

fn main() -> std::io::Result<()> {
    let tagger = Tagger::load("data")?;
    let tokens = tagger.tag("A sede da empresa é grande.");

    for t in tokens {
        println!("{}\t{}\t{:?}", t.word, t.upos, t.diacritic);
    }
    Ok(())
}
```

> O pacote se chama `bcde-tagger` (com hífen) no `Cargo.toml`, mas o identificador para `use` é `bcde_tagger` (com underscore). Isso é uma regra do Rust: nomes de pacote aceitam hífen, mas identificadores de módulo não. O Cargo faz a conversão automaticamente.

#### API pública

| Item | Descrição |
|------|-----------|
| `Tagger::load(base: &str) -> io::Result<Tagger>` | Carrega os 4 JSONs do diretório `base` |
| `Tagger::tag(&self, text: &str) -> Vec<Token>` | Processa uma frase |
| `Tagger::tag_batch(&self, texts: &[String]) -> Vec<Vec<Token>>` | Processa várias frases |
| `Token` | `{ word: String, upos: String, diacritic: Option<String>, sense: Option<String>, resolver_level: Option<String> }` |
| `tokenize_mwt(text: &str) -> Vec<String>` | Tokenizador isolado |
| `ALL_POS: &[&str]` | As 17 classes UD na ordem canônica |

#### Uso como serviço

Como o `Tagger` é `Send + Sync`, pode ser compartilhado entre threads:

```rust
use bcde_tagger::Tagger;
use std::sync::Arc;
use std::thread;

let tagger = Arc::new(Tagger::load("data")?);

let mut handles = vec![];
for i in 0..4 {
    let t = Arc::clone(&tagger);
    handles.push(thread::spawn(move || {
        t.tag(&format!("Frase {}", i))
    }));
}

for h in handles {
    let tokens = h.join().unwrap();
    // ...
}
```

### Python

```python
from tagger_python import Tagger

t = Tagger()  # auto-detecta paths

# Saída completa
for tok in t.tag("A sede da empresa é grande."):
    print(tok)
# [{'word': 'A', 'upos': 'DET', 'diacritic': None, ...},
#  {'word': 'sede', 'upos': 'NOUN', 'diacritic': 'séde',
#   'sense': 'seat', 'resolver_level': 'full'}, ...]

# Só POS
t.pos_only("A sede da empresa é grande.")
# ['DET', 'NOUN', 'ADP', 'DET', 'NOUN', 'AUX', 'ADJ', 'PUNCT']

# Com acento correto
t.tag_with_diacritic("Ele tem sede de justiça.")
# 'Ele tem sêde de justiça .'

# Batch (rápido)
t.tag_batch(["frase 1", "frase 2", "frase 3"])
```

---

## Formato de saída

Cada token é um dict com 2 campos sempre e 3 extras para homógrafos.

| Campo | Sempre? | Descrição |
|-------|:-------:|-----------|
| `word` | ✓ | Token de superfície |
| `upos` | ✓ | Classe POS (17 UD) |
| `diacritic` | Homógrafos | Forma acentuada (`séde`, `sêde`, `pôrto`) |
| `sense` | Homógrafos | Label semântico (`seat`, `thirst`, `harbour`) |
| `resolver_level` | Homógrafos | `full`, `pw`, `prev`, `next`, `cls`, `upos`, `prior` |

---

## Acurácia

### POS global

| Split | Frases | Tokens | Acurácia |
|-------|-------:|-------:|:--------:|
| Train | 200.000 | 2.534.159 | **98.96%** |
| Val | 110.007 | 1.439.572 | **98.72%** |
| Test | 110.546 | 1.448.986 | **98.72%** |

Sem overfitting — train e val próximos.

### POS por classe (val)

| Classe | n | Acc | Classe | n | Acc |
|--------|---:|:---:|--------|---:|:---:|
| NOUN | 359.330 | 98.77% | ADP | 180.278 | 99.66% |
| PROPN | 9.316 | 86.39% | CCONJ | 22.879 | 99.97% |
| VERB | 180.038 | 98.49% | SCONJ | 38.599 | 93.63% |
| AUX | 34.038 | 99.63% | NUM | 6.044 | 98.31% |
| ADJ | 79.465 | 95.36% | INTJ | 471 | 49.68% |
| ADV | 37.220 | 98.56% | PUNCT | 157.502 | 99.99% |
| PRON | 43.227 | 96.03% | SYM | 59 | 100.00% |
| DET | 290.899 | 99.84% | X | 185 | 52.97% |

### Diacríticos (val)

| Split | Anotações | Acertos | Acurácia |
|-------|----------:|--------:|:--------:|
| Train | 80.319 | 77.858 | 96.94% |
| Val | 35.064 | 34.366 | **98.01%** |
| Test | 34.901 | 34.192 | **97.97%** |

### Diacríticos por palavra (val, n ≥ 100)

| Palavra | n | Acc | Palavra | n | Acc |
|---------|---:|:---:|---------|---:|:---:|
| gosto | 167 | 86.2% | aceno | 121 | 94.2% |
| colmo | 118 | 89.8% | troco | 106 | 94.3% |
| sossego | 75 | 90.7% | desacordo | 126 | 94.4% |
| apelo | 122 | 91.0% | espeto | 112 | 94.6% |
| seco | 200 | 91.0% | cor | 360 | 94.7% |
| coro | 137 | 91.2% | desgosto | 115 | 94.8% |
| toco | 92 | 91.3% | conforto | 115 | 94.8% |
| zelo | 37 | 91.9% | domo | 118 | 94.9% |
| desmantelo | 103 | 92.2% | tola | 139 | 95.0% |
| toldo | 130 | 92.3% | arroto | 101 | 95.1% |
| azedo | 105 | 92.4% | desconforto | 144 | 95.1% |
| gozo | 145 | 92.4% | abrolho | 126 | 95.2% |
| entorno | 108 | 92.6% | desespero | 126 | 95.2% |
| rogo | 122 | 92.6% | golfo | 85 | 95.3% |
| congelo | 84 | 92.9% | solto | 85 | 95.3% |
| adorno | 99 | 92.9% | desdobro | 107 | 95.3% |
| reboco | 86 | 93.0% | engodo | 113 | 95.6% |
| topo | 118 | 93.2% | emperro | 114 | 95.6% |
| choro | 135 | 93.3% | sopeso | 92 | 95.7% |
| redobro | 91 | 93.4% | empeno | 92 | 95.7% |
| gelo | 127 | 93.7% | decoro | 117 | 95.7% |
| contorno | 98 | 93.9% | relevo | 95 | 95.8% |

**Palavras com 100% de acurácia (val, n ≥ 80):** `atropelo`, `rego`, `torno`, `acerto`, `arrojo`, `abono`, `aperto`, `desenredo`, `desaforo`, `estofo`, `despojo`, `forro`, `dobro`, `fosso`, `desempeno`, `desvelo`, `arremesso`, `soma`.

### Nível de confiança do resolver (val)

| Nível | Acertos | % |
|-------|--------:|--:|
| full | 14.410 | 41.9% |
| pw | 11.351 | 33.0% |
| prev | 7.202 | 21.0% |
| next | 1.301 | 3.8% |
| cls | 88 | 0.3% |
| upos | 14 | 0.04% |
| prior | 0 | 0% |

96% dos acertos vêm dos 3 níveis mais específicos.

---

## Benchmarks

Ambiente: Google Colab, single-thread.

### Modelo

| Etapa | ms/frase | palavras/s |
|-------|:--------:|-----------:|
| features + CRF | 0.185 | 72.207 |
| + resolver | 0.195 | 68.465 |
| batch | 0.196 | 68.081 |

### Tokenizador

| Tokenizador | ms/frase | palavras/s |
|-------------|:--------:|-----------:|
| Stanza (batch 64) | 1.322 | 10.117 |
| regex+MWT | 0.020 | ~50.000 |

### End-to-end

| Configuração | ms/frase | frases/s |
|--------------|:--------:|---------:|
| Stanza, sem batch | 12.465 | 80 |
| Stanza, com batch | 1.448 | 690 |
| **regex+MWT (1 thread)** | **0.103** | **9.722** |
| **regex+MWT (4 workers)** | **~0.025** | **~40.000** |

### Estimativas práticas

| Volume | Tempo (1 worker) |
|--------|:----------------:|
| 1.000 frases | 0.10 s |
| 10.000 frases | 1.03 s |
| 100.000 frases | 10.29 s |
| 1.000.000 frases | 102.86 s |
| 10.000.000 frases | 1028.58 s |

---

## Tokenização

O tokenizador é regex + expansão estática de contrações (MWT).

**Regex base:**

```
d'|\w+(?:[-']\w+)*|[^\w\s]
```

**Expansão MWT** (~80 contrações):

| Entrada | Saída |
|---------|-------|
| `do` | `de` + `o` |
| `pelo` | `por` + `o` |
| `à` | `a` + `a` |
| `nesta` | `em` + `esta` |

**Regra de ambiguidade:** `nos` e `vos` só expandem se não forem pronome.

- `nos abandalhemo` → `nos` (pronome)
- `nos carros` → `em` + `os` (contração)

**Concordância com Stanza:** 99.75% em 2.000 frases do val. As divergências são apenas `d' água`, pronome `nos` e abreviações.

---

## Desambiguação de homógrafos

O resolver v7 usa **backoff hierárquico de 7 níveis**:

| Nível | Chave | min_count |
|-------|-------|:---------:|
| full | `(upos, prev_w, next_w, prev_u, next_u, prev2_w, next2_w)` | 3 |
| pw | `(upos, prev_w, next_w)` | 3 |
| prev | `(upos, prev_w)` | 2 |
| next | `(upos, next_w)` | 2 |
| cls | `(upos, prev_u, next_u)` | 3 |
| upos | `(upos,)` | 2 |
| prior | Forma majoritária global | — |

**122 palavras** têm resolver treinado (das 131 da tabela).

**Exemplos:**

```
A sede da empresa é grande.
→ sede = NOUN, diac = séde, sense = seat, via = full

Ele tem sede de justiça.
→ sede = NOUN, diac = sêde, sense = thirst, via = prev

O pelo do gato é macio.
→ pelo = NOUN, diac = pêlo, sense = hair, via = full

Ele foi pelo caminho mais longo.
→ pelo = ADP, diac = pelo, sense = by_the, via = full
```

---

## Datasets e fontes

### Corpus de treino

| Dataset | Frases | Origem |
|---------|-------:|--------|
| `dataset_final.jsonl` | 1.621.269 | Bosque + fontes antigas |
| `dataset_val_bifonia_sentencas.jsonl` | 500.000 | Bifonia + sentenças sintéticas |

**Dataset unificado:** 2.202.947 frases (após deduplicação), 28.882.948 tokens, 906.848 com anotação de sentido.

### Fontes lexicais

| Fonte | Licença | Uso |
|-------|:-------:|-----|
| [fserb/pt-br](https://github.com/fserb/pt-br) | MIT | Conjugações, verbos, léxico |
| [ime.usp.br/~pf/dicios](https://www.ime.usp.br/~pf/dicios/) | CC BY | Lista de palavras |
| [Portal da Língua Portuguesa](https://www.portaldalinguaportuguesa.org/) | Livre acesso | Scraping de palavras |
| [TigreGotico/bifonia](https://github.com/TigreGotico/bifonia) | CC BY-SA 4.0 | Validação de homógrafos |
| [bifonia-pt-homographs](https://huggingface.co/datasets/TigreGotico/bifonia-pt-homographs) | CC BY-SA 4.0 | Dataset de validação |
| [UD Portuguese Bosque](https://universaldependencies.org/treebanks/pt_bosque/) | CC BY-SA 4.0 | Anotação POS |

### Anotação

As frases foram geradas sinteticamente a partir de sementes de palavras homógrafas + listas de palavras únicas, enviadas em lotes para geração de frases naturais. Foram geradas mais de **1.6 milhões de sentenças** entre 40 e 180 caracteres, posteriormente anotadas pelo **Bifonia** (sentidos) + **Stanza** (POS).

> Muitas frases têm estrutura robótica, mas a variedade de contextos é suficiente para o CRF aprender os padrões de desambiguação.

### Tabelas

Três tabelas construídas sobre o corpus unificado:

| Tabela | Conteúdo | Tamanho |
|--------|----------|--------:|
| `always_X` | Palavras 100% X (min_count=10) | 14.022 (NOUN) a 2 (SCONJ) |
| `never_X` | Palavras nunca X (min_count=10) | ~55K por classe |
| `prior` | Distribuição de POS por palavra | 203K palavras |
| `ambig` | Grupos de ambiguidade | 12.069 palavras |

---

## Limitações

### POS

- **PROPN (86.4%)** — o Stanza anota a maioria dos nomes próprios como NOUN. O CRF herda esse erro.
- **ADJ ↔ NOUN (2.8%)** — ambiguidade real que o próprio Stanza erra.
- **SCONJ ↔ ADP (3.6%)** — ambiguidade real (`que`, `como`, `para`).
- **INTJ e PART** — amostra minúscula, ruído estatístico.

### Diacríticos

- **`gosto` (86%)**, **`sossego` (91%)**, **`zelo` (92%)** — 1ª pessoa do singular que é homógrafa de substantivo comum. O corpus tem mais ocorrências do substantivo.
- **~70% dos erros de diacríticos** são ruído de anotação do corpus (conjugações erradas como `aborto` em vez de `abortou`).

### Tokenizador

- **MWT ambíguo** — `nos` pode ser pronome ou contração, resolvido por heurística.
- **Dígitos e símbolos** — `20h`, `R$`, `2.5` podem divergir do Stanza (~0.1%).
- **Abreviações** — `B.` (letra + ponto) — Stanza une, regex separa.

### O que o modelo NÃO faz

- NER (entidades nomeadas)
- Parsing (dependências sintáticas)
- Lematização
- Desambiguação semântica geral (só para os 131 homógrafos)
- Texto informal (internetês: `vc`, `q`, `pq`)
- Outras variantes (pt-PT)

---

## Licença

**MIT**. Veja [LICENSE](LICENSE).

### Atribuições

Partes do inventário lexical derivam de fontes com licenças específicas:

| Fonte | Licença |
|-------|:-------:|
| `fserb/pt-br` | MIT |
| `ime.usp.br/~pf/dicios` | CC BY |
| `TigreGotico/bifonia` | CC BY-SA 4.0 |
| `UD Portuguese Bosque` | CC BY-SA 4.0 |
| Portal da Língua Portuguesa | Livre acesso |

O modelo treinado (CRF, tabelas, resolver) é um artefato derivado desses dados. Embora o **código** seja MIT, os **dados** mantêm suas licenças originais. Ao redistribuir, atribua as fontes conforme suas licenças.

---

## Citação

```bibtex
@misc{bcde-tagger,
  title={BCDE-tagger: Fast POS tagging and homograph disambiguation for Brazilian Portuguese},
  author={BCDE},
  year={2026},
  url={https://github.com/bcdeosce/BCDE-tagger}
}
```

---

## Agradecimentos

- [Tigre Gotico](https://github.com/TigreGotico) — pela biblioteca Bifonia e pelos datasets de homógrafos
- [Fernando Serboncini](https://github.com/fserb) — pelo repositório `pt-br`
- [Paulo Feofiloff](https://www.ime.usp.br/~pf/) — pela lista de palavras do português brasileiro
- [Universal Dependencies](https://universaldependencies.org/) — pelo treebank Bosque
- Comunidade Stanza — pela anotação inicial do corpus

---

<div align="center">

Feito com ❤️ para a comunidade pt-BR.

</div>

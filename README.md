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
| `tag(text)` | Lista de tokens com POS, diacrítico e sentido (MWT expandido) |
| `tag_surface(text)` | Idem, mas MWT preservados (`do`, `pelo` como token único) |
| `tag_tokens(tokens)` | Pipeline direto sobre tokens já tokenizados |
| `diacritize(text)` | Texto com diacríticos aplicados (`sede` → `séde`/`sêde`) |
| `tag_batch(texts)` | Processa lista de textos em paralelo |
| POS tagging | 17 classes Universal Dependencies |
| MWT expansion | 80 contrações expandidas automaticamente |
| Diacrítico | 131 homógrafos desambiguados por contexto |
| Sentido | Label semântico (`seat`, `thirst`, `hair`, etc.) |
| CLI | `echo "frase" \| ./bcde-tagger data [--surface\|--diacritize]` |
| Biblioteca Rust | Crate importável (`use bcde_tagger::Tagger`) |
| Binding Python | Via subprocess com processo persistente |

---

```
texto cru
    │
    ▼
[tokenizer.rs]              regex + expansão MWT (com heurística pra MWT ambíguos)
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
    ├──► tag():         Vec<Token> com MWT expandido
    ├──► tag_surface(): Vec<Token> com MWT preservado
    └──► diacritize():  String com diacríticos aplicados
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
│   ├── tabelas_v3.json           # always/never/prior/ambig (17 MB)
│   ├── crf_weights.json          # pesos do CRF (14 MB)
│   ├── resolver_v7.json          # resolver de diacríticos (3 MB)
│   └── diacriticos_table.json    # 131 homógrafos → sentido (50 KB)
├── python/
│   └── tagger_python.py          # binding Python via subprocess
└── src/
    ├── lib.rs                    # ponto de entrada da biblioteca
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
# Modo padrão — tokens expandidos (MWT decomposto)
echo "A sede da empresa é grande." | ./target/release/bcde-tagger data

# Modo superfície — MWT preservado (do, pelo, deste como token único)
echo "O pelo do gato é macio." | ./target/release/bcde-tagger data --surface

# Modo diacritize — só texto com diacríticos aplicados
echo "A sede da empresa é grande." | ./target/release/bcde-tagger data --diacritize
```

Saída modo padrão (MWT expandido):

```
A       DET
sede    NOUN    diac=séde      sense=seat     via=full
de      ADP
a       DET
empresa NOUN
é       AUX
grande  ADJ
.       PUNCT
```

Saída `--surface` (MWT preservado, UPOS do primeiro componente):

```
O       DET
pelo    NOUN    diac=pêlo      sense=hair     via=pw
do      ADP
gato    NOUN
é       AUX
macio   ADJ
.       PUNCT
```

Saída `--diacritize` (texto → texto):

```
A séde da empresa é grande.
```

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

    // POS + diacríticos + sentidos (MWT expandido)
    for t in tagger.tag("A sede da empresa é grande.") {
        println!("{}\t{}\t{:?}", t.word, t.upos, t.diacritic);
    }

    // MWT preservado na saída (do, pelo, deste como token único)
    for t in tagger.tag_surface("O pelo do gato é macio.") {
        println!("{}\t{}\t{:?}", t.word, t.upos, t.diacritic);
    }

    // Só o texto com diacríticos aplicados
    let texto = tagger.diacritize("Ele tem sede de justiça.");
    println!("{}", texto);  // "Ele tem sêde de justiça."

    Ok(())
}
```

> O pacote se chama `bcde-tagger` (com hífen) no `Cargo.toml`, mas o identificador para `use` é `bcde_tagger` (com underscore). Isso é uma regra do Rust: nomes de pacote aceitam hífen, mas identificadores de módulo não. O Cargo faz a conversão automaticamente.

#### API pública

| Item | Descrição |
|------|-----------|
| `Tagger::load(base: &str) -> io::Result<Tagger>` | Carrega os 4 JSONs do diretório `base` |
| `Tagger::tag(&self, text: &str) -> Vec<Token>` | Pipeline completo (MWT expandido) |
| `Tagger::tag_surface(&self, text: &str) -> Vec<Token>` | Idem, mas MWT preservado |
| `Tagger::tag_tokens(&self, tokens: &[String]) -> Vec<Token>` | Pipeline direto sobre tokens |
| `Tagger::diacritize(&self, text: &str) -> String` | Texto com diacríticos aplicados |
| `Token` | `{ word, upos, diacritic: Option<String>, sense: Option<String>, resolver_level: Option<String> }` |
| `tokenize_mwt(text: &str) -> Vec<String>` | Tokenizador isolado |
| `tokenize_mwt_with_spans(text: &str) -> (Vec<String>, Vec<(usize, usize)>)` | Tokenizador com spans |
| `ALL_POS: &[&str]` | As 17 classes UD na ordem canônica |

### Python

```python
from tagger_python import Tagger

t = Tagger()  # auto-detecta paths relativos ao repositório

# Saída completa
for tok in t.tag("A sede da empresa é grande."):
    print(tok)
# [{'word': 'A', 'upos': 'DET', 'diacritic': None, ...},
#  {'word': 'sede', 'upos': 'NOUN', 'diacritic': 'séde',
#   'sense': 'seat', 'resolver_level': 'full'}, ...]

# Só POS
t.pos_only("A sede da empresa é grande.")
# ['DET', 'NOUN', 'ADP', 'DET', 'NOUN', 'AUX', 'ADJ', 'PUNCT']

# Texto com diacríticos aplicados
t.diacritize("Ele tem sede de justiça.")
# 'Ele tem sêde de justiça.'

t.diacritize("O pelo do gato é macio.")
# 'O pêlo do gato é macio.'

# MWT preservado na saída
t.tag_surface("O pelo do gato é macio.")
# [{'word': 'O', 'upos': 'DET', ...},
#  {'word': 'pelo', 'upos': 'NOUN', 'diacritic': 'pêlo', ...}, ...]

# Batch (rápido)
t.tag_batch(["frase 1", "frase 2", "frase 3"])
```

## Formato de saída

### Modo `tag` (padrão) e `tag_surface`

Cada token é um dict com 2 campos sempre e 3 extras para homógrafos.

| Campo | Sempre? | Descrição |
|-------|:-------:|-----------|
| `word` | ✓ | Token de superfície |
| `upos` | ✓ | Classe POS (17 UD) |
| `diacritic` | Homógrafos | Forma acentuada (`séde`, `sêde`, `pôrto`) |
| `sense` | Homógrafos | Label semântico (`seat`, `thirst`, `harbour`) |
| `resolver_level` | Homógrafos | `full`, `pw`, `prev`, `next`, `cls`, `upos`, `prior` |

**Diferença entre `tag` e `tag_surface`:**

- `tag`: MWT são **expandidos** na saída (`do` → `de`+`o`, `pelo` → `por`+`o`). O número de tokens de saída pode ser maior que o de entrada.
- `tag_surface`: MWT são **preservados** (`do`, `pelo`, `deste` como tokens únicos). O UPOS atribuído ao MWT é o do primeiro componente. O número de tokens de saída é igual ao de entrada.

### Modo `diacritize`

Devolve uma **string** — o texto de entrada com diacríticos aplicados nas palavras que o resolver souber desambiguar.

Preserva espaços, pontuação, capitalização e a superfície original (`do`, `pelo`, `à` ficam como estão).

**Exemplos:**

| entrada | saída |
|---------|-------|
| `A sede da empresa é grande.` | `A séde da empresa é grande.` |
| `Ele tem sede de justiça.` | `Ele tem sêde de justiça.` |
| `O pelo do gato é macio.` | `O pêlo do gato é macio.` |
| `Ele foi pelo caminho mais longo.` | `Ele foi pelo caminho mais longo.` |
| `Pelo a cenoura e depois ralo.` | `Pelo a cenoura e depois ralo.` |
| `O porto de Santos é grande.` | `O pôrto de Santos é grande.` |
| `Eu porto um documento sempre.` | `Eu pórto um documento sempre.` |

Se a palavra não for um dos 131 homógrafos da tabela, ou se o resolver não souber desambiguar com confiança, a palavra sai inalterada.
## Acurácia

### POS global

| Split | Frases | Tokens | Acurácia |
|-------|-------:|-------:|:--------:|
| Val | 110.007 | 1.439.280 | **98,73%** |
| Test | 110.546 | 1.448.986 | **98,73%** |

Sem overfitting — val e test próximos.

### POS por classe (val)

| Classe | n | Acc | Classe | n | Acc |
|--------|---:|:---:|--------|---:|:---:|
| NOUN | 359.284 | 98,73% | ADP | 180.261 | 99,61% |
| PROPN | 9.263 | 86,39% | CCONJ | 22.878 | 99,95% |
| VERB | 180.026 | 98,58% | SCONJ | 38.594 | 93,90% |
| AUX | 34.037 | 99,64% | NUM | 6.031 | 98,14% |
| ADJ | 79.451 | 95,46% | INTJ | 471 | 50,53% |
| ADV | 37.211 | 98,68% | PUNCT | 157.483 | 99,99% |
| PRON | 43.133 | 96,06% | SYM | 57 | 100,00% |
| DET | 290.893 | 99,86% | X | 185 | 56,22% |

### Diacríticos (val)

| Métrica | Valor |
|---------|------:|
| Anotações avaliadas | 35.064 |
| Acertos | 34.371 |
| **Acurácia global** | **98,02%** |

### Diacríticos por palavra (val, n ≥ 90)

| Palavra | n | Acc | Palavra | n | Acc |
|---------|---:|:---:|---------|---:|:---:|
| congelo | 84 | 66,7% | espeto | 112 | 94,6% |
| gosto | 167 | 86,2% | cor | 360 | 94,7% |
| coro | 137 | 89,8% | desgosto | 115 | 94,8% |
| colmo | 118 | 89,8% | conforto | 115 | 94,8% |
| sossego | 75 | 90,7% | domo | 118 | 94,9% |
| apelo | 122 | 91,0% | tola | 139 | 95,0% |
| seco | 200 | 91,0% | arroto | 101 | 95,1% |
| desmantelo | 103 | 91,3% | desconforto | 144 | 95,1% |
| adorno | 99 | 91,9% | abrolho | 126 | 95,2% |
| toldo | 130 | 92,3% | desespero | 126 | 95,2% |
| azedo | 105 | 92,4% | golfo | 85 | 95,3% |
| gozo | 145 | 92,4% | solto | 85 | 95,3% |
| entorno | 108 | 92,6% | desdobro | 107 | 95,3% |
| rogo | 122 | 92,6% | engodo | 113 | 95,6% |
| reboco | 86 | 93,0% | emperro | 114 | 95,6% |
| topo | 118 | 93,2% | sopeso | 92 | 95,7% |
| choro | 135 | 93,3% | empeno | 92 | 95,7% |
| redobro | 91 | 93,4% | decoro | 117 | 95,7% |
| gelo | 127 | 93,7% | relevo | 95 | 95,8% |
| contorno | 98 | 93,9% | torre | 148 | 95,9% |
| aceno | 121 | 94,2% | arrepelo | 125 | 96,0% |
| troco | 106 | 94,3% | escabelo | 100 | 96,0% |
| desacordo | 126 | 94,4% | transtorno | 151 | 96,0% |
| jorro | 108 | 96,3% | emprego | 196 | 96,4% |
| esmero | 111 | 96,4% | sobro | 86 | 96,5% |
| repelo | 89 | 96,6% | logro | 92 | 96,7% |
| desgelo | 132 | 97,0% | desafogo | 99 | 97,0% |
| desemprego | 676 | 97,0% | choco | 140 | 97,1% |
| colher | 177 | 97,2% | forma | 730 | 97,3% |
| enredo | 113 | 97,4% | tempero | 117 | 97,4% |
| cerco | 118 | 97,5% | cerro | 118 | 97,5% |
| retorno | 118 | 97,5% | desconsolo | 82 | 97,6% |
| apego | 127 | 97,6% | rola | 86 | 97,7% |
| novelo | 98 | 98,0% | aborto | 100 | 98,0% |
| olho | 151 | 98,0% | degelo | 102 | 98,0% |
| polo | 521 | 98,1% | cobro | 108 | 98,2% |
| rolo | 108 | 98,2% | soco | 110 | 98,2% |
| arremedo | 112 | 98,2% | consolo | 118 | 98,3% |
| sopro | 123 | 98,4% | desprezo | 130 | 98,5% |
| acordo | 370 | 98,7% | para | 10.356 | 98,9% |
| governo | 269 | 98,9% | bola | 93 | 98,9% |
| conserto | 191 | 99,0% | desassossego | 194 | 99,0% |
| soldo | 103 | 99,0% | desemperro | 106 | 99,1% |
| corte | 459 | 99,1% | encosto | 120 | 99,2% |
| lobo | 649 | 99,2% | despego | 133 | 99,3% |
| peso | 680 | 99,3% | jogo | 274 | 99,3% |
| posto | 589 | 99,3% | desapego | 299 | 99,3% |
| selo | 1.099 | 99,4% | sobre | 3.157 | 99,4% |
| erro | 343 | 99,4% | molho | 1.042 | 99,5% |
| porto | 355 | 99,7% | | | |

**Palavras com 100% de acurácia (val, n ≥ 80):** `atropelo`, `rego`, `torno`, `acerto`, `arrojo`, `abono`, `aperto`, `desenredo`, `desaforo`, `estofo`, `despojo`, `forro`, `dobro`, `fosso`, `desempeno`, `desvelo`, `arremesso`, `soma`.

### Nível de confiança do resolver (val)

| Nível | Acertos | % |
|-------|--------:|--:|
| full | 14.452 | 42,0% |
| pw | 11.340 | 33,0% |
| prev | 7.176 | 20,9% |
| next | 1.304 | 3,8% |
| cls | 83 | 0,2% |
| upos | 16 | 0,05% |
| prior | 0 | 0% |

96% dos acertos vêm dos 3 níveis mais específicos. O resolver usa contexto real — não cai em fallback.

### Diacritize — texto → texto (val)

Avaliação end-to-end da função `diacritize`: compara a string de saída com o gabarito reconstruído (aplicando `diac_table[w][sense]` no texto original nos índices anotados pelo Bifonia).

| Métrica | Valor |
|---------|------:|
| Frases com anotação | 45.237 |
| Frases 100% corretas | 36.486 |
| **Acurácia por frase** | **80,66%** |
| Anotações individuais corretas | 34.371 / 35.064 |
| **Acurácia por anotação** | **98,02%** |

A diferença entre "80,66% por frase" e "98,02% por anotação" é esperada: uma frase com 3 anotações só conta como correta se acertar as 3. Com 98% de acerto por anotação e 2 anotações por frase, o acerto por frase cai para ~96%; com 3+ anotações, cai para ~94%. O 80,66% reflete a distribuição real de anotações por frase no corpus de validação (muitas frases têm 3–5 anotações).

---

## Benchmarks

Ambiente: Google Colab, single-thread, processo persistente (modelo carregado 1× e alimentado via pipe).

### Modelo

| Etapa | ms/frase | palavras/s |
|-------|:--------:|-----------:|
| `tag` (completo) | 0.083 | 161.571 |
| `diacritize` (texto → texto) | 0.130 | 103.125 |

### End-to-end (com tokenizador regex+MWT)

| Modo | frases/s | palavras/s |
|------|---------:|-----------:|
| `tag` | **12.084** | **161.571** |
| `tag_surface` | ~11.500 | ~155.000 |
| `diacritize` | **7.712** | **103.125** |

### Comparação com outras abordagens

| Abordagem | frases/s | Acurácia POS |
|-----------|---------:|:------------:|
| Stanza (CPU, batch 64) | 690 | 98.72% |
| Stanza (GPU, batch 64) | ~2.500 | 98.72% |
| **BCDE-tagger (single-thread)** | **12.084** | **98.73%** |
| **BCDE-tagger (4 workers)** | **~40.000** | 98.73% |

### Estimativas práticas

| Volume | Tempo (1 worker) | Tempo (4 workers) |
|--------|:----------------:|:-----------------:|
| 1.000 frases | 0.08 s | 0.02 s |
| 10.000 frases | 0.83 s | 0.21 s |
| 100.000 frases | 8.28 s | 2.07 s |
| 1.000.000 frases | 82.75 s | 20.69 s |
| 10.000.000 frases | 827.5 s | 206.9 s |
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

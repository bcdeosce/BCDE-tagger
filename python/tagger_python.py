"""
BCDE-tagger — Python wrapper.

Uso:
    from tagger_python import Tagger

    t = Tagger()  # auto-detecta paths
    t.tag("A sede da empresa é grande.")
    t.tag_surface("O pelo do gato é macio.")
    t.diacritize("Ele tem sede de justiça.")

CLI:
    python tagger_python.py "frase"
    echo "frase" | python tagger_python.py
    python tagger_python.py --diacritize "frase"
"""
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class Tagger:
    def __init__(self,
                 binary: Optional[Path] = None,
                 data_dir: Optional[Path] = None):
        """
        Args:
            binary:   caminho pro binário Rust. Default: <root>/target/release/bcde-tagger
            data_dir: pasta com os 4 JSONs. Default: <root>/data
        """
        root = Path(__file__).resolve().parent.parent

        if binary is None:
            binary = root / "target" / "release" / "bcde-tagger"
        if data_dir is None:
            data_dir = root / "data"

        self.binary = Path(binary)
        self.data_dir = Path(data_dir)

        if not self.binary.exists():
            raise FileNotFoundError(
                f"binário não encontrado: {self.binary}\n"
                f"rode 'cargo build --release' na raiz do projeto"
            )
        if not self.data_dir.exists():
            raise FileNotFoundError(f"pasta data/ não encontrada: {self.data_dir}")

        # Verifica os 4 JSONs (resolver v7 ou v6)
        for f in ["tabelas_v3.json", "crf_weights.json", "diacriticos_table.json"]:
            if not (self.data_dir / f).exists():
                raise FileNotFoundError(f"falta {f} em {self.data_dir}")
        if not (self.data_dir / "resolver_v7.json").exists() and \
           not (self.data_dir / "resolver_v6.json").exists():
            raise FileNotFoundError(f"falta resolver_v7.json (ou v6) em {self.data_dir}")

    # ── API principal ─────────────────────────────────────────────

    def tag(self, text: str) -> List[Dict[str, Optional[str]]]:
        """Pipeline completo. MWT expandido na saída (do → de + o)."""
        return self.tag_batch([text])[0]

    def tag_batch(self, texts: List[str]) -> List[List[Dict[str, Optional[str]]]]:
        """Processa várias frases numa só chamada ao binário."""
        if not texts:
            return []
        entrada = "\n".join(texts) + "\n"
        r = subprocess.run(
            [str(self.binary), str(self.data_dir)],
            input=entrada,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"tagger falhou (código {r.returncode}): {r.stderr}")
        return self._parse(r.stdout, len(texts))

    def tag_surface(self, text: str) -> List[Dict[str, Optional[str]]]:
        """Igual a tag(), mas MWT preservados (do, pelo, deste como token único)."""
        return self.tag_surface_batch([text])[0]

    def tag_surface_batch(self, texts: List[str]) -> List[List[Dict[str, Optional[str]]]]:
        """tag_surface em lote."""
        if not texts:
            return []
        entrada = "\n".join(texts) + "\n"
        r = subprocess.run(
            [str(self.binary), str(self.data_dir), "--surface"],
            input=entrada,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"tagger falhou (código {r.returncode}): {r.stderr}")
        return self._parse(r.stdout, len(texts))

    def diacritize(self, text: str) -> str:
        """Retorna o texto com diacríticos aplicados nas palavras desambiguadas."""
        return self.diacritize_batch([text])[0]

    def diacritize_batch(self, texts: List[str]) -> List[str]:
        """diacritize em lote."""
        if not texts:
            return []
        entrada = "\n".join(texts) + "\n"
        r = subprocess.run(
            [str(self.binary), str(self.data_dir), "--diacritize"],
            input=entrada,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"tagger falhou (código {r.returncode}): {r.stderr}")
        return r.stdout.rstrip("\n").split("\n")

    # ── Helpers ───────────────────────────────────────────────────

    def pos_only(self, text: str) -> List[str]:
        """Só a lista de POS."""
        return [t["upos"] for t in self.tag(text)]

    def tag_with_diacritic(self, text: str) -> str:
        """Alias de diacritize() — mantido por compatibilidade."""
        return self.diacritize(text)

    def tag_simple(self, text: str) -> List[Tuple[str, str]]:
        """Lista de (word, upos) — sem diacríticos."""
        return [(t["word"], t["upos"]) for t in self.tag(text)]

    # ── Parser interno ────────────────────────────────────────────

    def _parse(self, output: str, n_texts: int) -> List[List[Dict[str, Optional[str]]]]:
        result: List[List[Dict[str, Optional[str]]]] = []
        current: List[Dict[str, Optional[str]]] = []
        for line in output.split("\n"):
            if not line.strip():
                if current:
                    result.append(current)
                    current = []
                continue
            parts = line.split("\t")
            tok: Dict[str, Optional[str]] = {
                "word": parts[0],
                "upos": parts[1] if len(parts) > 1 else "",
                "diacritic": None,
                "sense": None,
                "resolver_level": None,
            }
            for extra in parts[2:]:
                if extra.startswith("diac="):
                    tok["diacritic"] = extra[5:]
                elif extra.startswith("sense="):
                    tok["sense"] = extra[6:]
                elif extra.startswith("via="):
                    tok["resolver_level"] = extra[4:]
            current.append(tok)
        if current:
            result.append(current)
        while len(result) < n_texts:
            result.append([])
        return result


# ── API rápida (singleton) ────────────────────────────────────────
_default: Optional[Tagger] = None

def _get() -> Tagger:
    global _default
    if _default is None:
        _default = Tagger()
    return _default

def tag(text: str) -> List[Dict[str, Optional[str]]]:
    return _get().tag(text)

def tag_batch(texts: List[str]) -> List[List[Dict[str, Optional[str]]]]:
    return _get().tag_batch(texts)

def tag_surface(text: str) -> List[Dict[str, Optional[str]]]:
    return _get().tag_surface(text)

def diacritize(text: str) -> str:
    return _get().diacritize(text)

def pos_only(text: str) -> List[str]:
    return _get().pos_only(text)

def tag_simple(text: str) -> List[Tuple[str, str]]:
    return _get().tag_simple(text)


# ── CLI ───────────────────────────────────────────────────────────
def _print_tokens(toks):
    for tok in toks:
        extra = ""
        if tok.get("diacritic"):
            extra = (f"  diac={tok['diacritic']}  "
                     f"sense={tok.get('sense')}  "
                     f"via={tok.get('resolver_level')}")
        print(f"{tok['word']:<15} {tok['upos']:<6}{extra}")

if __name__ == "__main__":
    args = sys.argv[1:]
    mode = "tag"
    if args and args[0] in ("--diacritize", "--surface", "--pos"):
        mode = args[0].lstrip("-")
        args = args[1:]

    t = Tagger()

    # Frase passada como argumento
    if args:
        texto = " ".join(args)
        if mode == "diacritize":
            print(t.diacritize(texto))
        elif mode == "surface":
            _print_tokens(t.tag_surface(texto))
        elif mode == "pos":
            print(" ".join(t.pos_only(texto)))
        else:
            _print_tokens(t.tag(texto))
        sys.exit(0)

    # stdin
    if mode == "diacritize":
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line.strip():
                print(t.diacritize(line))
    elif mode == "surface":
        for line in sys.stdin:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            print(f">>> {line}")
            _print_tokens(t.tag_surface(line))
            print()
    elif mode == "pos":
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line.strip():
                print(" ".join(t.pos_only(line)))
    else:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            print(f">>> {line}")
            _print_tokens(t.tag(line))
            print()

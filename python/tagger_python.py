"""
BCDE-tagger — Python wrapper.

Uso:
    from tagger_python import Tagger
    t = Tagger()
    t.tag("A sede da empresa é grande.")
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
            binary:   caminho pro binário Rust. Default: <root>/target/release/tagger
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

        # Verifica se os 4 arquivos existem
        for f in ["tabelas_v3.json", "crf_weights.json",
                  "resolver_v7.json", "diacriticos_table.json"]:
            if not (self.data_dir / f).exists():
                # resolver_v7 pode ser v6
                if f == "resolver_v7.json" and (self.data_dir / "resolver_v6.json").exists():
                    continue
                raise FileNotFoundError(f"falta {f} em {self.data_dir}")

    def tag(self, text: str) -> List[Dict[str, Optional[str]]]:
        """Uma frase → lista de tokens."""
        return self.tag_batch([text])[0]

    def tag_batch(self, texts: List[str]) -> List[List[Dict[str, Optional[str]]]]:
        """Várias frases em uma execução do binário."""
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

    # ── helpers ──────────────────────────────────────────────────

    def tag_simple(self, text: str) -> List[Tuple[str, str]]:
        """Retorna [(word, upos), ...] — sem diacríticos."""
        return [(t["word"], t["upos"]) for t in self.tag(text)]

    def tag_with_diacritic(self, text: str) -> str:
        """Retorna texto com diacríticos aplicados."""
        return " ".join(
            t.get("diacritic") or t["word"]
            for t in self.tag(text)
        )

    def pos_only(self, text: str) -> List[str]:
        """Retorna só a lista de POS."""
        return [t["upos"] for t in self.tag(text)]

    def tag_surface(self, text: str) -> List[Dict[str, Optional[str]]]:
        """Como tag(), mas preserva MWT de superfície (do, da, no, ...)."""
        r = subprocess.run(
            [str(self.binary), str(self.data_dir), "--surface"],
            input=text + "\n",
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"tagger falhou (código {r.returncode}): {r.stderr}")
        res = self._parse(r.stdout, 1)
        return res[0] if res else []
# ── API rápida ────────────────────────────────────────────────────
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

def tag_simple(text: str) -> List[Tuple[str, str]]:
    return _get().tag_simple(text)

def tag_with_diacritic(text: str) -> str:
    return _get().tag_with_diacritic(text)


# ── CLI ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tagger_python.py 'frase'")
        print("     echo 'frase' | python tagger_python.py")
        sys.exit(1)

    t = Tagger()

    if len(sys.argv) > 1:
        # Frase como argumento
        for tok in t.tag(" ".join(sys.argv[1:])):
            extra = ""
            if tok["diacritic"]:
                extra = f"  diac={tok['diacritic']}  sense={tok['sense']}  via={tok['resolver_level']}"
            print(f"{tok['word']:<15} {tok['upos']:<6}{extra}")
    else:
        # Lê do stdin
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            print(f">>> {line}")
            for tok in t.tag(line):
                extra = ""
                if tok["diacritic"]:
                    extra = f"  diac={tok['diacritic']}"
                print(f"  {tok['word']:<15} {tok['upos']:<6}{extra}")
            print()

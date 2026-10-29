"""Catálogo ordenado de los 37 videos (solo lectura). ID estable por video."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "analysis"

GROUPS = [
    ("E2", "1.- estrategia 2 (importante)"),
    ("RSR", "2.- PATRON RSR Y SRS (importante)"),
    ("C0907", "3.- CLASES EN VIVO resumido/3.1.- CLASE 9 JULIO"),
    ("C1306", "3.- CLASES EN VIVO resumido/3.2.- CLASE 13 JUNIO"),
]


def _num(name: str) -> int:
    # "1) x.mp4", "1 - x.mp4", "... PARTE 12.mp4" -> número de orden
    m = re.search(r"PARTE\s+(\d+)", name) or re.match(r"\s*(\d+)", name)
    return int(m.group(1))


def catalog():
    """Lista [(id, Path)] en orden de carpeta y, dentro, por número (no alfabético)."""
    out = []
    for prefix, folder in GROUPS:
        files = sorted((ROOT / folder).glob("*.mp4"), key=lambda p: _num(p.name))
        for p in files:
            n = _num(p.name)
            vid = f"{prefix}-P{n:02d}" if prefix.startswith("C") else f"{prefix}-{n:02d}"
            out.append((vid, p))
    return out


if __name__ == "__main__":
    for vid, p in catalog():
        print(vid, p.relative_to(ROOT))

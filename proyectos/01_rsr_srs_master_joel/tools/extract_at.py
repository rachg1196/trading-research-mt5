"""Extrae fotogramas puntuales pedidos por los agentes ("Fotogramas que faltan").

Uso:  .venv\\Scripts\\python.exe tools\\extract_at.py C0907-P05 01:23 01:24.5 ...
Guarda en analysis/frames/<ID>/<ID>_MMmSSs_extra.jpg y los añade a index.md. Solo lee el video.
"""
import sys
from pathlib import Path

import av

sys.path.insert(0, str(Path(__file__).resolve().parent))
from videos import ANALYSIS, catalog


def secs(s: str) -> float:
    m, _, r = s.partition(":")
    return float(m) * 60 + float(r) if r else float(m)


def main():
    vid, times = sys.argv[1], [secs(t) for t in sys.argv[2:]]
    path = dict(catalog())[vid]
    d = ANALYSIS / "frames" / vid
    rows = []
    with av.open(str(path)) as c:
        st = c.streams.video[0]
        for t in sorted(times):
            c.seek(int(t / st.time_base), stream=st, backward=True)
            for fr in c.decode(st):
                if float(fr.pts * st.time_base) >= t:
                    break
            img = fr.to_image()
            if fr.rotation:
                img = img.rotate(fr.rotation, expand=True)
            frac = f"{int(round(t % 1 * 100)):02d}" if t % 1 else ""  # 00m57s25: varios por segundo
            name = f"{vid}_{int(t // 60):02d}m{int(t % 60):02d}s{frac}_extra.jpg"
            img.resize((1280, round(img.height * 1280 / img.width))).save(d / name, quality=85)
            rows.append(f"| {int(t // 60):02d}:{int(t % 60):02d} | {name} | extra (pedido) | |")
            print(name)
    with (d / "index.md").open("a", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()

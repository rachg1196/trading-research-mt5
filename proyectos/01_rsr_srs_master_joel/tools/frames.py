"""Etapa 2: extracción reanudable de fotogramas de los gráficos.

Un fotograma se guarda (JPG, 1280 px de ancho) cuando ocurre algo de esto:
  - kw:    Master Joel pronuncia un término clave (lista KEYWORDS, solo para *buscar*, no son
           reglas); se toma en la palabra y 2 s después (lo dibuja tras decirlo)
  - cambio: la imagen cambia de forma visible respecto al último fotograma guardado
  - pausa: han pasado MAX_GAP s sin guardar nada (cobertura mínima)
Requiere el .json de la Etapa 1. Salida: analysis/frames/<ID>/*.jpg + index.json + index.md.
Un video con index.json ya existente se salta. Los videos solo se leen.

Uso:  .venv\\Scripts\\python.exe tools\\frames.py [--only ID ...]
"""
import argparse, json, re, sys, time, unicodedata
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from videos import ROOT, ANALYSIS, catalog

TRANS = ANALYSIS / "transcripts"
OUT = ANALYSIS / "frames"
STEP = 1.0          # s entre muestras evaluadas
DIFF = 6.0          # diferencia media (0-255) en miniatura gris 96x54 para considerar "cambio"
MAX_GAP = 20.0      # s máximos sin guardar fotograma
KW_DELAY = 2.0      # s tras la palabra clave para el segundo fotograma

# Términos de búsqueda pedidos por el usuario + títulos de los videos. Sin acentos, minúsculas.
KEYWORDS = [
    r"pisos?", r"techos?", r"rsr", r"srs", r"ptp", r"tpt", r"r\s?s\s?r", r"s\s?r\s?s",
    r"patron(es)?", r"entrad\w*", r"entr(o|a|amos|ar|aria)", r"confirm\w*", r"invalid\w*",
    r"temporalidad\w*", r"ztd", r"marca\w*", r"tendencia\w*", r"stop\w*", r"tp", r"take",
    r"profit", r"objetivo\w*", r"compra\w*", r"venta\w*", r"vend\w*", r"compr\w*",
    # vocabulario que Master Joel usa de hecho (RSR-01 @ 00:18-01:55)
    r"resistencias?", r"soportes?", r"zonas?", r"romp\w*", r"rupt\w*", r"vela\w*", r"apoy\w*",
]
KW_RE = re.compile(r"\b(" + "|".join(KEYWORDS) + r")\b")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def keyword_times(tr):
    """[(t, palabra, frase)] para cada palabra clave dicha en el video."""
    hits = []
    for seg in tr["segments"]:
        for w in seg["words"]:
            if KW_RE.search(norm(w["w"]).strip(" .,;:¿?¡!")):
                hits.append((w["s"], w["w"].strip(), seg["text"]))
    return hits


def text_at(tr, t):
    for seg in tr["segments"]:
        if seg["start"] - 0.5 <= t <= seg["end"] + 0.5:
            return f"[{ts(seg['start'])}] {seg['text']}"
    return ""


def process(vid, path):
    tr = json.loads((TRANS / f"{vid}.json").read_text(encoding="utf-8"))
    hits = keyword_times(tr)
    targets = {}  # segundo -> motivo
    for t, word, _ in hits:
        for tt, why in ((t, f"kw:{word}"), (t + KW_DELAY, f"kw+2s:{word}")):
            targets.setdefault(int(tt), why)

    d = OUT / vid
    d.mkdir(parents=True, exist_ok=True)
    kept, last_thumb, last_t, next_t = [], None, -1e9, 0.0
    with av.open(str(path)) as c:
        st = c.streams.video[0]
        st.thread_type = "AUTO"
        for fr in c.decode(st):
            t = float(fr.pts * st.time_base)
            if t < next_t:
                continue
            next_t = t + STEP
            img = fr.to_image()
            if fr.rotation:  # E2-* vienen 888x1920 con rotación 90 en metadatos (D-005)
                img = img.rotate(fr.rotation, expand=True)
            thumb = np.asarray(img.convert("L").resize((96, 54)), dtype=np.float32)
            diff = 255.0 if last_thumb is None else float(np.abs(thumb - last_thumb).mean())
            why = targets.get(int(t))
            if why is None and diff >= DIFF:
                why = f"cambio:{diff:.1f}"
            if why is None and t - last_t >= MAX_GAP:
                why = "pausa"
            if why is None:
                continue
            name = f"{vid}_{int(t // 60):02d}m{int(t % 60):02d}s.jpg"
            if not (d / name).exists():  # reanudación: no reescribir lo ya exportado
                w = 1280
                img.resize((w, round(img.height * w / img.width))).save(d / name, quality=85)
            kept.append({"t": round(t, 2), "mmss": ts(t), "file": name, "why": why,
                         "diff": round(diff, 1), "speech": text_at(tr, t)})
            last_thumb, last_t = thumb, t

    idx = {"id": vid, "source": tr["source"], "duration": tr["duration"],
           "params": {"step": STEP, "diff": DIFF, "max_gap": MAX_GAP, "kw_delay": KW_DELAY},
           "keyword_hits": [{"t": t, "mmss": ts(t), "word": w} for t, w, _ in hits],
           "frames": kept}
    md = [f"# Fotogramas {vid} — {tr['source']}", "",
          f"{len(kept)} fotogramas · {len(hits)} palabras clave · motivo: kw = término dicho, "
          f"cambio = la imagen cambió, pausa = cobertura cada {MAX_GAP:.0f} s", "",
          "| Tiempo | Archivo | Motivo | Habla en ese momento |", "|---|---|---|---|"]
    md += [f"| {k['mmss']} | {k['file']} | {k['why']} | {k['speech'].replace('|', '/')} |"
           for k in kept]
    (d / "index.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    tmp = d / "index.json.tmp"
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(d / "index.json")
    return len(kept), len(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    for vid, path in catalog():
        if a.only and vid not in a.only:
            continue
        if (OUT / vid / "index.json").exists():
            print(f"{vid} ya hecho")
            continue
        if not (TRANS / f"{vid}.json").exists():
            print(f"{vid} sin transcripción, se omite")
            continue
        t0 = time.time()
        n, k = process(vid, path)
        print(f"{vid} ok: {n} fotogramas, {k} palabras clave, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

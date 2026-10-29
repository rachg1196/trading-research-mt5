"""Control de calidad de la Etapa 1: segmentos dudosos por video (solo lectura)."""
import json, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from videos import ANALYSIS, catalog

SUSPECT = re.compile(r"subt[ií]tul|amara|suscr[ií]b|gracias por ver", re.I)

print(f"{'ID':<10} {'dur':>6} {'segs':>5} {'voz_s':>6} {'%voz':>5} {'p<-1':>5} {'rep':>4} {'sosp':>4}")
for vid, _ in catalog():
    d = json.loads((ANALYSIS / "transcripts" / f"{vid}.json").read_text(encoding="utf-8"))
    segs = d["segments"]
    speech = sum(s["end"] - s["start"] for s in segs)
    low = [s for s in segs if s["avg_logprob"] < -1.0]
    reps = sum(c - 1 for c in Counter(s["text"].lower() for s in segs if len(s["text"]) > 15).values() if c > 1)
    sus = [s for s in segs if SUSPECT.search(s["text"])]
    print(f"{vid:<10} {d['duration']:>6.0f} {len(segs):>5} {speech:>6.0f} {100*speech/d['duration']:>4.0f}% "
          f"{len(low):>5} {reps:>4} {len(sus):>4}")
    for s in low + sus:
        print(f"    {int(s['start'])//60:02d}:{int(s['start'])%60:02d} lp={s['avg_logprob']} "
              f"{s['text'][:90]}".encode("ascii", "replace").decode())

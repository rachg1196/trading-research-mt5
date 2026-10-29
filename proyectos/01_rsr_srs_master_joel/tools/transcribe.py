"""Etapa 1: transcripción reanudable de los 37 videos con faster-whisper large-v3.

Uso:  .venv\\Scripts\\python.exe tools\\transcribe.py [--device cuda|cpu] [--only ID ...]
Salida: analysis/transcripts/<ID>.json y <ID>.md. Un video con .json ya existente se salta,
así que basta con relanzar el script si se interrumpe. Los videos solo se leen.
"""
import argparse, json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from videos import ROOT, ANALYSIS, catalog

# DLLs CUDA (cuBLAS/cuDNN) instaladas como wheels en el venv (ver DECISIONS D-004)
_nv = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
for sub in ("cublas", "cudnn", "cuda_nvrtc"):
    d = _nv / sub / "bin"
    if d.is_dir():
        os.add_dll_directory(str(d))
        os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from faster_whisper import WhisperModel  # noqa: E402

MODEL = "large-v3"
OUT = ANALYSIS / "transcripts"
LOG = ANALYSIS / "transcribe.log"


def ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def log(msg: str):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line.encode("ascii", "replace").decode(), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    todo = [(v, p) for v, p in catalog() if not a.only or v in a.only]
    pending = [(v, p) for v, p in todo if not (OUT / f"{v}.json").exists()]
    log(f"inicio: {len(todo)} videos, {len(todo) - len(pending)} ya hechos, {len(pending)} pendientes")
    if not pending:
        return

    compute = "float16" if a.device == "cuda" else "int8"
    model = WhisperModel(MODEL, device=a.device, compute_type=compute)

    for vid, path in pending:
        t0 = time.time()
        segments, info = model.transcribe(
            str(path), language="es", word_timestamps=True,
            vad_filter=True, condition_on_previous_text=False, beam_size=5,
        )
        segs = [{
            "start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
            "avg_logprob": round(s.avg_logprob, 3), "no_speech_prob": round(s.no_speech_prob, 3),
            "words": [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2),
                       "p": round(w.probability, 3)} for w in (s.words or [])],
        } for s in segments]
        rel = path.relative_to(ROOT).as_posix()
        data = {"id": vid, "source": rel, "duration": round(info.duration, 2),
                "model": MODEL, "device": a.device, "compute_type": compute,
                "language": info.language, "segments": segs}

        md = [f"# {vid} — {rel}", "",
              f"Duración {ts(info.duration)} · modelo {MODEL} ({a.device}/{compute}) · "
              f"transcripción automática **sin revisar**", ""]
        md += [f"[{ts(s['start'])}–{ts(s['end'])}] {s['text']}" for s in segs]

        # escritura atómica: el .json (marca de "hecho") se escribe al final
        (OUT / f"{vid}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        tmp = OUT / f"{vid}.json.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(OUT / f"{vid}.json")
        log(f"{vid} ok: {len(segs)} segmentos, audio {ts(info.duration)}, {time.time() - t0:.0f}s")

    log("fin")


if __name__ == "__main__":
    main()

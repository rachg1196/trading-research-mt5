# -*- coding: utf-8 -*-
"""Transcribe a texto el audio de los videos .mp4 que esten en la carpeta del proyecto.
Usa faster-whisper (modelo 'small', se descarga una sola vez). Resultado: resultados\\transcripciones\\<video>.txt"""
import os, glob, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "resultados", "transcripciones"); os.makedirs(OUT, exist_ok=True)
import traceback
LOG = os.path.join(BASE, "resultados", "transcribir_log.txt")
def log(m):
    print(m, flush=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(str(m) + "\n")
open(LOG, "w", encoding="utf-8").close()
try:
    from faster_whisper import WhisperModel
except Exception:
    log("ERROR importando faster-whisper:\n" + traceback.format_exc()); sys.exit(1)
import wave, numpy as np
def leer_wav(ruta):
    with wave.open(ruta, "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
# se usan los audios .wav (16 kHz) de la carpeta audio\ ; si no existen, el .mp4
videos = sorted(glob.glob(os.path.join(BASE, "audio", "*.wav"))) or sorted(glob.glob(os.path.join(BASE, "*.mp4")))
if not videos:
    log("No hay videos .mp4 en la carpeta del proyecto."); sys.exit(0)
log(f"Videos encontrados: {len(videos)}")
log("Cargando modelo de voz a texto (la primera vez se descarga, ~500 MB)...")
try:
    modelo = WhisperModel("small", device="cpu", compute_type="int8")
except Exception:
    log("ERROR cargando/descargando el modelo:\n" + traceback.format_exc()); sys.exit(1)
for v in videos:
    nombre = os.path.splitext(os.path.basename(v))[0]
    if os.path.exists(os.path.join(OUT, nombre + ".txt")):
        log(f"Ya transcrito, se omite: {nombre}"); continue
    log(f"Transcribiendo: {nombre}")
    lineas = []
    try:
        entrada = leer_wav(v) if v.lower().endswith(".wav") else v
        segs, info = modelo.transcribe(entrada, language="es", vad_filter=True)
        for sg in segs:
            m, sec = divmod(int(sg.start), 60)
            linea = f"[{m:02d}:{sec:02d}] {sg.text.strip()}"
            print(linea, flush=True); lineas.append(linea)
    except Exception:
        log("ERROR transcribiendo " + nombre + ":\n" + traceback.format_exc()); continue
    with open(os.path.join(OUT, nombre + ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
log("Listo. Transcripciones en resultados\\transcripciones")

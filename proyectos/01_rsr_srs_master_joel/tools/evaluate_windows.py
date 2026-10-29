"""D-017 (6 y 7): compara las señales del detector con lo que Master Joel marcó en cada ventana de los videos.
NO es un backtest: no simula entradas, salidas ni resultados. Solo cuenta señales.

- Ventanas y marcas: analysis/cases/windows.json (A1). Solo ventanas con CSV de velas reales.
- Una marca "tomó"/"válido" es positiva; "descartó" es negativa; "señaló sin juzgar" se informa aparte.
- Acierto por hora: señal en la misma dirección con la misma vela 0. Acierto por zona: además, niveles dentro
  de sus rectángulos ampliados por max(error de lectura, 0,25 velas medias) (tolerancia propuesta, D-017).
- Señales agrupadas por (dirección, vela 0) como en la propuesta S-10, sin aplicarla en el detector.
- Separación sin sobreajuste: se eligen parámetros con las ventanas de E2 (curso grabado, ago-sep 2025) y se
  comprueban con las de las clases en vivo (jun-jul 2025), que no intervienen en la elección.

Uso:  .venv\\Scripts\\python.exe tools\\evaluate_windows.py   → analysis/cases/eval_results.json
"""
import csv
import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rsr_srs import Candle, Params, detect  # noqa: E402

WARMUP = 150
GRID = dict(max_width=[1.5, 2.0, 3.0, 4.0], max_fake=[2, 3, 4, 5], max_total=[16, 24, 40], avg_n=[20, 50],
            zone_pick=["all", "shortest"], single_candle=["inside", "vela0"], wick=["b", "c"])
POSITIVE, NEGATIVE = {"tomó", "válido"}, {"descartó"}


@lru_cache(maxsize=None)
def load(path):
    with (ROOT / path).open(encoding="utf-8") as f:
        return tuple(Candle(r["time"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
                     for r in csv.DictReader(f))


def windows():
    w = json.loads((ROOT / "analysis/cases/windows.json").read_text(encoding="utf-8"))
    w = w["windows"] if isinstance(w, dict) else w
    return [x for x in w if x.get("csv") and x.get("start") and x.get("end")]


def in_band(level, band, tol):
    return band is not None and min(band) - tol <= level <= max(band) + tol


def eval_window(win, params):
    candles = load(win["csv"])
    times = [c.time for c in candles]
    i0 = max(0, next((i for i, t in enumerate(times) if t >= win["start"]), len(times)) - WARMUP)
    i1 = next((i for i, t in enumerate(times) if t > win["end"]), len(times))
    sig, _ = detect(candles[i0:i1], params)
    sig = [s for s in sig if win["start"] <= s.vela0.time <= win["end"]]
    groups = {}
    for s in sig:
        groups.setdefault((s.direction, s.vela0.time), []).append(s)
    out = {"signals": len(sig), "grouped": len(groups), "marks": [], "unmarked": 0}
    used = set()
    for m in win["marks"]:
        key = (m.get("direction"), m.get("vela0"))
        g = groups.get(key, [])
        zone_ok = any(in_band(s.level_high, m.get("upper_band"), max(m.get("read_error") or 0, 0.25 * s.avg_candle))
                      and in_band(s.level_low, m.get("lower_band"), max(m.get("read_error") or 0, 0.25 * s.avg_candle))
                      for s in g)
        if g:
            used.add(key)
        out["marks"].append({"case": m.get("case"), "action": m.get("action"), "hit_time": bool(g),
                             "hit_zone": zone_ok})
    out["unmarked"] = len([k for k in groups if k not in used])
    out["unmarked_list"] = sorted(f"{d} {t}" for d, t in groups if (d, t) not in used)
    return out


def score(results):
    """Resumen de un conjunto de ventanas para una combinación de parámetros."""
    pos = [m for r in results for m in r["marks"] if m["action"] in POSITIVE]
    neg = [m for r in results for m in r["marks"] if m["action"] in NEGATIVE]
    return {"positives": len(pos), "pos_hit_time": sum(m["hit_time"] for m in pos),
            "pos_hit_zone": sum(m["hit_zone"] for m in pos), "negatives": len(neg),
            "neg_signaled": sum(m["hit_time"] for m in neg),
            "signals_grouped": sum(r["grouped"] for r in results),
            "unmarked_grouped": sum(r["unmarked"] for r in results)}


def run_combo(values):
    params = Params(**dict(zip(GRID, values)))
    wins = windows()
    res = {w["id"]: eval_window(w, params) for w in wins}
    train = [res[w["id"]] for w in wins if w["video"].startswith("E2-")]
    test = [res[w["id"]] for w in wins if not w["video"].startswith("E2-")]
    return dict(zip(GRID, values)), score(train), score(test), res


def main():
    combos = list(itertools.product(*GRID.values()))
    with ProcessPoolExecutor() as ex:
        rows = list(ex.map(run_combo, combos, chunksize=8))
    # Elección SOLO con E2: más positivos con su zona, luego por hora, menos descartes suyos señalados,
    # menos señales sin marcar.
    key = lambda r: (r[1]["pos_hit_zone"], r[1]["pos_hit_time"], -r[1]["neg_signaled"], -r[1]["unmarked_grouped"])
    best = max(rows, key=key)
    ref2 = next(r for r in rows if r[0] == dict(max_width=2.0, max_fake=2, max_total=16, avg_n=20, zone_pick="all",
                                                single_candle="inside", wick="b"))
    out = {"grid": GRID, "n_combos": len(combos), "windows": [w["id"] for w in windows()],
           "train": [w["id"] for w in windows() if w["video"].startswith("E2-")],
           "chosen": {"params": best[0], "train": best[1], "test": best[2], "per_window": best[3]},
           "ref2": {"params": ref2[0], "train": ref2[1], "test": ref2[2], "per_window": ref2[3]},
           "top10_train": [{"params": r[0], "train": r[1], "test": r[2]} for r in sorted(rows, key=key)[-10:]]}
    (ROOT / "analysis/cases/eval_results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                                           encoding="utf-8")
    for name in ("chosen", "ref2"):
        print(name, out[name]["params"], "\n  train", out[name]["train"], "\n  test ", out[name]["test"])


if __name__ == "__main__":
    main()

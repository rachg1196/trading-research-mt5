"""D-019: mide la ZTD horizontal (misma TF; H1 y H4 como columna informativa) y el F-5 redefinido como filtros
opcionales. NO es un backtest. Misma base y misma separación curso (E2) / clases que tools/measure_filters.py.
Una señal se conserva si al menos una de sus zonas (S-10) cumple la condición. No se eligen valores finales.

Uso:  .venv\\Scripts\\python.exe tools\\measure_ztd.py   → analysis/cases/ztd_results.json
"""
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from evaluate_windows import NEGATIVE, POSITIVE, WARMUP, load, windows  # noqa: E402
from measure_filters import BASE  # noqa: E402
from rsr_srs import detect  # noqa: E402
from rsr_srs.ztd import horizontal_ztd, htf_index  # noqa: E402

TF_MIN = {"M2": 2, "M5": 5, "M15": 15, "H1": 60, "H4": 240}
HTF_AVG_N = 20       # velas de la TF mayor para su vela media (medición, no recomendado)


def htf_file(sym, tf, day):
    for f in sorted(glob.glob(str(ROOT / f"analysis/mt5/history/{sym}_{tf}_*.csv"))):
        a, b = os.path.basename(f)[:-4].split("_")[2:4]
        if a[:10] <= day < b[:10]:
            return "analysis/mt5/history/" + os.path.basename(f)
    return None


def ztd_same(cands, z, d, L, dist):
    return horizontal_ztd(cands, d, z["start"], z["low"], z["high"], z["avg_candle"], L, dist,
                          BASE.ztd_margin, BASE.max_width)


def ztd_htf(cands, z, d, sym, tf, L, dist):
    t0 = cands[z["start"]].time
    f = htf_file(sym, tf, t0[:10])
    if f is None:
        return None
    h = load(f)
    n = htf_index(h, t0, TF_MIN[tf])
    if n < HTF_AVG_N + 3:
        return None
    avg = sum(x.high - x.low for x in h[n - HTF_AVG_N:n]) / HTF_AVG_N
    return horizontal_ztd(list(h[:n]), d, n, z["low"], z["high"], avg, L, dist, BASE.ztd_margin, BASE.max_width)


RULES = {  # nombre: predicado(velas, zona, dirección, símbolo)
    "ZTD-h misma TF (L 100, d 1)": lambda c, z, d, s: ztd_same(c, z, d, 100, 1.0) is not None,
    "ZTD-h misma TF (L 50, d 1)": lambda c, z, d, s: ztd_same(c, z, d, 50, 1.0) is not None,
    "ZTD-h misma TF (L 200, d 1)": lambda c, z, d, s: ztd_same(c, z, d, 200, 1.0) is not None,
    "ZTD-h misma TF (L 100, d 0,5)": lambda c, z, d, s: ztd_same(c, z, d, 100, 0.5) is not None,
    "ZTD-h misma TF (L 100, d 2)": lambda c, z, d, s: ztd_same(c, z, d, 100, 2.0) is not None,
    "ZTD-h misma TF + primer toque": lambda c, z, d, s: (r := ztd_same(c, z, d, 100, 1.0)) is not None
                                                       and r["primer_toque"],
    "ZTD-h H1 (L 50, d 1) [informativa]": lambda c, z, d, s: ztd_htf(c, z, d, s, "H1", 50, 1.0) is not None,
    "ZTD-h H4 (L 50, d 1) [informativa]": lambda c, z, d, s: ztd_htf(c, z, d, s, "H4", 50, 1.0) is not None,
    "F-5 nuevo: zona intacta ≥ 0,5": lambda c, z, d, s: (r := z["measures"]["F5_room"]) is None or r >= 0.5,
    "F-5 nuevo: zona intacta ≥ 1": lambda c, z, d, s: (r := z["measures"]["F5_room"]) is None or r >= 1,
    "F-5 nuevo: zona intacta ≥ 2": lambda c, z, d, s: (r := z["measures"]["F5_room"]) is None or r >= 2,
    "F-5 nuevo: zona intacta ≥ 3": lambda c, z, d, s: (r := z["measures"]["F5_room"]) is None or r >= 3,
}


def sym_of(csv_path):
    return os.path.basename(csv_path).split("_")[0]


def run_windows():
    out = {}
    for w in windows():
        candles = load(w["csv"])
        times = [c.time for c in candles]
        i0 = max(0, next((i for i, t in enumerate(times) if t >= w["start"]), len(times)) - WARMUP)
        i1 = next((i for i, t in enumerate(times) if t > w["end"]), len(times))
        cands = list(candles[i0:i1])
        sig, _ = detect(cands, BASE)
        out[w["id"]] = (cands, [s for s in sig if w["start"] <= s.vela0.time <= w["end"]], sym_of(w["csv"]))
    return out


def summarize(runs, subset, rule):
    n = pos = pos_hit = neg = neg_hit = 0
    for w in subset:
        cands, sig, sym = runs[w["id"]]
        kept = [s for s in sig if rule is None or any(rule(cands, z, s.direction, sym) for z in s.zones)]
        keys = {(s.direction, s.vela0.time) for s in kept}
        n += len(kept)
        for m in w["marks"]:
            hit = (m.get("direction"), m.get("vela0")) in keys
            if m.get("action") in POSITIVE:
                pos, pos_hit = pos + 1, pos_hit + hit
            elif m.get("action") in NEGATIVE:
                neg, neg_hit = neg + 1, neg_hit + hit
    return {"señales": n, "válidos": pos, "válidos_acertados": pos_hit, "descartes": neg, "descartes_señalados": neg_hit}


def per_day(rule):
    """Señales al día por TF (mediana y rango entre archivos continuos de M2/M5/M15)."""
    by_tf = {}
    for f in sorted(glob.glob(str(ROOT / "analysis/mt5/history/*.csv"))):
        name = os.path.basename(f)
        tf = name.split("_")[1]
        if tf not in ("M2", "M5", "M15"):
            continue
        cands = list(load("analysis/mt5/history/" + name))
        if len(cands) < 300:
            continue
        sig, _ = _cached_detect(name, cands)
        sig = [s for s in sig if s.vela0_index >= WARMUP]
        kept = [s for s in sig if rule is None or any(rule(cands, z, s.direction, sym_of(name)) for z in s.zones)]
        days = (len(cands) - WARMUP) * TF_MIN[tf] / 1440
        by_tf.setdefault(tf, []).append(round(len(kept) / days, 1))
    return {tf: {"min": min(v), "mediana": sorted(v)[len(v) // 2], "max": max(v)} for tf, v in by_tf.items()}


_DET = {}


def _cached_detect(name, cands):
    if name not in _DET:
        _DET[name] = detect(cands, BASE)
    return _DET[name]


def main():
    wins = windows()
    train = [w for w in wins if w["video"].startswith("E2-")]
    test = [w for w in wins if not w["video"].startswith("E2-")]
    runs = run_windows()
    b_tr, b_te = summarize(runs, train, None), summarize(runs, test, None)
    rows = [{"filtro": "base (sin filtro)", "curso": b_tr, "clases": b_te, "por_día": per_day(None)}]
    for name, rule in RULES.items():
        tr, te = summarize(runs, train, rule), summarize(runs, test, rule)
        rows.append({"filtro": name, "curso": tr, "clases": te, "por_día": per_day(rule)})
    for r in rows:
        for part, b in (("curso", b_tr), ("clases", b_te)):
            x = r[part]
            x["quita_%"] = round(100 * (b["señales"] - x["señales"]) / b["señales"], 1)
            x["válidos_perdidos"] = b["válidos_acertados"] - x["válidos_acertados"]
            x["descartes_eliminados"] = b["descartes_señalados"] - x["descartes_señalados"]
    (ROOT / "analysis/cases/ztd_results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                                                          encoding="utf-8")
    for r in rows:
        c, k, pdd = r["curso"], r["clases"], r["por_día"]
        print(f"{r['filtro']:<38} curso -{c['quita_%']:>5}% vál-{c['válidos_perdidos']} desc-{c['descartes_eliminados']}"
              f" | clases -{k['quita_%']:>5}% vál-{k['válidos_perdidos']} desc-{k['descartes_eliminados']}"
              f" | día M2 {pdd.get('M2', {}).get('mediana')} M5 {pdd['M5']['min']}-{pdd['M5']['mediana']}-{pdd['M5']['max']}"
              f" M15 {pdd['M15']['mediana']}")


if __name__ == "__main__":
    main()

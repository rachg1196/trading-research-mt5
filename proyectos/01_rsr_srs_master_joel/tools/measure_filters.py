"""D-018 (3-6): efecto de cada filtro sobre las señales de las ventanas de los videos. NO es un backtest.

Base: parámetros elegidos con E2 en D-017, sin filtros. Cada señal (S-10) guarda las medidas F-1..F-6 de cada
zona que la respalda; un filtro conserva la señal si al menos una de sus zonas lo cumple (lo mismo que haría el
detector con el filtro activado). La anchura (P-2) cambia la estructura, así que se vuelve a ejecutar.
Separación: curso grabado (E2) para elegir, clases para comprobar. Solo filtros sueltos y parejas (pocos
ejemplos etiquetados). No se eligen valores finales.

Uso:  .venv\\Scripts\\python.exe tools\\measure_filters.py   → analysis/cases/filters_results.json
"""
import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from evaluate_windows import NEGATIVE, POSITIVE, WARMUP, load, windows  # noqa: E402
from rsr_srs import Params, detect  # noqa: E402

BASE = Params(max_width=2.0, max_fake=5, max_total=24, avg_n=50, zone_pick="all", single_candle="inside", wick="b")
FILTERS = {  # nombre: (medida, "min" = exige >= valor | "max" = exige <= valor, valores)
    "F-1 caída previa (mín.)": ("F1_prior_move", "min", [0.5, 1, 2, 3]),
    "F-2 vela 0 (máx.)": ("F2_vela0_size", "max", [1, 1.5, 2, 3]),
    "F-3 cierre lejos (máx.)": ("F3_close_dist", "max", [0.25, 0.5, 0.8, 1.0]),
    "F-4 rechazo (máx.)": ("F4_rejection", "max", [0.25, 0.4, 0.5]),
    "F-5 espacio libre (mín.)": ("F5_room", "min", [0.5, 1, 2]),
    "F-6 cruces (máx.)": ("F6_crossings", "max", [1, 2, 3, 4]),
}
WIDTHS = [1.0, 1.5, 2.0]   # P-2 por debajo de la base (2,0): solo puede quitar señales


def passes(zone, rule):
    key, op, v = rule
    x = zone["measures"][key]
    if x is None:               # F-5 sin obstáculo previo: no hay nada cerca
        return True
    return x >= v if op == "min" else x <= v


def collect(params):
    """Señales por ventana: [(ventana, señal)], con la ventana ya recortada como en evaluate_windows."""
    out = {}
    for w in windows():
        candles = load(w["csv"])
        times = [c.time for c in candles]
        i0 = max(0, next((i for i, t in enumerate(times) if t >= w["start"]), len(times)) - WARMUP)
        i1 = next((i for i, t in enumerate(times) if t > w["end"]), len(times))
        sig, _ = detect(candles[i0:i1], params)
        out[w["id"]] = [s for s in sig if w["start"] <= s.vela0.time <= w["end"]]
    return out


def summarize(sigs, rules, subset):
    """Cuenta señales, válidos acertados por hora y descartes señalados en un subconjunto de ventanas."""
    n = pos = pos_hit = neg = neg_hit = 0
    for w in subset:
        kept = [s for s in sigs[w["id"]] if any(all(passes(z, r) for r in rules) for z in s.zones)]
        keys = {(s.direction, s.vela0.time) for s in kept}
        n += len(kept)
        for m in w["marks"]:
            hit = (m.get("direction"), m.get("vela0")) in keys
            if m.get("action") in POSITIVE:
                pos, pos_hit = pos + 1, pos_hit + hit
            elif m.get("action") in NEGATIVE:
                neg, neg_hit = neg + 1, neg_hit + hit
    return {"señales": n, "válidos": pos, "válidos_acertados": pos_hit, "descartes": neg, "descartes_señalados": neg_hit}


def main():
    wins = windows()
    train = [w for w in wins if w["video"].startswith("E2-")]
    test = [w for w in wins if not w["video"].startswith("E2-")]
    runs = {wd: collect(replace(BASE, max_width=wd)) for wd in WIDTHS}
    base = runs[BASE.max_width]
    b_tr, b_te = summarize(base, [], train), summarize(base, [], test)

    def row(name, sigs, rules):
        tr, te = summarize(sigs, rules, train), summarize(sigs, rules, test)
        delta = lambda r, b: {"quita": b["señales"] - r["señales"], "quita_%": round(100 * (b["señales"] - r["señales"]) / b["señales"], 1),
                              "válidos_perdidos": b["válidos_acertados"] - r["válidos_acertados"],
                              "descartes_eliminados": b["descartes_señalados"] - r["descartes_señalados"]}
        return {"filtro": name, "curso": {**tr, **delta(tr, b_tr)}, "clases": {**te, **delta(te, b_te)}}

    singles = [row(f"P-2 anchura ≤ {wd}", runs[wd], []) for wd in WIDTHS if wd != BASE.max_width]
    options = [(f"{name} {v}", (key, op, v)) for name, (key, op, vals) in FILTERS.items() for v in vals]
    singles += [row(lbl, base, [rule]) for lbl, rule in options]
    # Parejas (máx. 2 filtros): de familias distintas, con o sin anchura menor.
    pairs = []
    for (l1, r1), (l2, r2) in itertools.combinations(options, 2):
        if r1[0] != r2[0]:
            pairs.append(row(f"{l1} + {l2}", base, [r1, r2]))
    for wd in WIDTHS:
        if wd != BASE.max_width:
            pairs += [row(f"P-2 anchura ≤ {wd} + {lbl}", runs[wd], [rule]) for lbl, rule in options]
    cands = singles + pairs
    # "Mejor" elegida SOLO con el curso: no pierde ningún válido del curso; quita más señales; luego elimina más
    # descartes. Se informa cómo se comporta en las clases.
    ok = [r for r in cands if r["curso"]["válidos_perdidos"] == 0]
    best = max(ok, key=lambda r: (r["curso"]["quita"], r["curso"]["descartes_eliminados"])) if ok else None
    out = {"base": {"params": BASE.__dict__, "curso": b_tr, "clases": b_te}, "singles": singles,
           "best_pair_or_single": best, "n_candidates": len(cands)}
    (ROOT / "analysis/cases/filters_results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                                              encoding="utf-8")
    print("base", b_tr, b_te)
    for r in singles:
        c, k = r["curso"], r["clases"]
        print(f"{r['filtro']:<32} curso: -{c['quita']:>3} ({c['quita_%']:>5}%) válidos-{c['válidos_perdidos']} desc-{c['descartes_eliminados']}"
              f" | clases: -{k['quita']:>3} ({k['quita_%']:>5}%) válidos-{k['válidos_perdidos']} desc-{k['descartes_eliminados']}")
    print("MEJOR (elegida con el curso):", json.dumps(best, ensure_ascii=False))


if __name__ == "__main__":
    main()

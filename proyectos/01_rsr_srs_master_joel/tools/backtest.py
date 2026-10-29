"""T15: backtest histórico según docs/BACKTEST_PLAN.md (D-020, D-021). Sin conexión operativa, sin órdenes.

Uso:  .venv\\Scripts\\python.exe tools\\backtest.py dev       → analysis/backtest/dev.json (revisión)
      .venv\\Scripts\\python.exe tools\\backtest.py holdout   → analysis/backtest/holdout.json (UNA sola vez)
Los dos modos calculan lo mismo; cada uno solo escribe los resultados de su parte.
"""
import bisect
import csv
import json
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rsr_srs import BUY, Candle, Detector, Params  # noqa: E402
from rsr_srs.ztd import broken_zones  # noqa: E402

HIST = ROOT / "analysis" / "mt5" / "history"
OUT = ROOT / "analysis" / "backtest"
START, CUT, END = "2025-01-02 00:00", "2026-04-04 00:00", "2026-10-17 23:59"   # plan §2
TF_MIN = {"M1": 1, "M5": 5, "M15": 15}
POINT = 0.01
SLIP, SLIP_SENS = 0.5, (0.0, 1.0)            # plan §3: 0,5 × spread; sensibilidad 0 × y 1 ×
REPS, SEED = 1000, 20261018                   # plan §5
BASE = Params(max_width=2.0, max_fake=5, max_total=24, avg_n=50, zone_pick="all", single_candle="inside",
              wick="b", measure_context=False)  # D-017; contexto desactivado (plan §8)
F3, F4 = 1.0, 0.4                             # variante (c)
ZTD_L, ZTD_D, ZTD_MARGIN, HTF_AVG_N = 50, 1.0, 0.5, 20   # variante (b), como en D-019
# Especificación leída en solo lectura el 18-10-2026: spread (puntos), modo de swap, swap compra, swap venta
SPEC = {"FlipX1": (100, 2, -1.0, -1.0), "FlipX2": (150, 2, -1.5, -1.5), "FlipX3": (200, 2, -2.0, -2.0),
        "FlipX4": (250, 2, -2.5, -2.5), "FlipX5": (300, 2, -3.0, -3.0), "FXVol20": (426, 5, -2.0, -2.0),
        "FXVol80": (1804, 5, -8.0, -8.0), "SFXVol20": (376, 5, -6.5, -6.5), "BreakX600": (130, 2, -5.0, -5.0)}
VARIANTS = ("a", "b", "c")
EXITS = {"4velas": 3, "mj2": 1, "mj3": 2}     # desplazamiento de la vela de salida desde la de entrada


def load(sym, tf, frm="2024-12-01T0000"):
    f = next(HIST.glob(f"{sym}_{tf}_{frm}_*.csv"))
    with f.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    t = [r["time"] for r in rows]
    a = {k: np.array([float(r[k]) for r in rows]) for k in ("open", "high", "low", "close", "spread")}
    return t, a


def spreads(sym, raw):
    """Plan §8.2: si la mediana del historial < 80 % de la especificación, el mayor de los dos en cada vela."""
    spec = SPEC[sym][0]
    prudent = np.median(raw) < 0.8 * spec
    return (np.maximum(raw, spec) if prudent else raw.copy()), bool(prudent)


def swap_cost(sym, buy, price, nights):
    """USD por 1 lote (contrato 1). Modo 2: valor por noche; modo 5: interés anual % sobre el precio / 360."""
    _, mode, sl, ss = SPEC[sym]
    v = sl if buy else ss
    return nights * (v if mode == 2 else v / 100 * price / 360)


def trade_pnl(o, c, sp, e, x, buy, slip):
    """Resultado en precio (= USD por lote) de entrar a la apertura de `e` y salir al cierre de `x`.
    Velas bid: la compra paga el spread al entrar; la venta, al salir. Deslizamiento = slip × spread."""
    if buy:
        return (c[x] - slip * sp[x] * POINT) - (o[e] + (1 + slip) * sp[e] * POINT)
    return (o[e] - slip * sp[e] * POINT) - (c[x] + (1 + slip) * sp[x] * POINT)


def nights_between(t_open, t_close):
    d0 = datetime.strptime(t_open[:10], "%Y-%m-%d")
    d1 = datetime.strptime(t_close[:10], "%Y-%m-%d")
    return (d1 - d0).days


def detect_all(t, a, n):
    """Detector causal sobre las n primeras velas (en dev no hace falta pasar de la última vela de la parte)."""
    d = Detector(BASE)
    sigs = []
    for i in range(n):
        s, _ = d.update(Candle(t[i], a["open"][i], a["high"][i], a["low"][i], a["close"][i]))
        sigs.extend(s)
        d.discards.clear()
        if i % 5000 == 0:   # zonas viejas: ya no pueden volver a crearse (fin >= i - P-5)
            d.used_zones = {z for z in d.used_zones if z[2] >= i - 2 * BASE.max_total}
    # S-10 añade zonas a una señal ya creada en la misma vela: por eso se guardan los objetos al final
    return sigs


def ztd_h4(sym, sigs, t, a):
    """Variante (b): ¿alguna zona de la señal tiene ZTD horizontal en H4? (definición de rsr_srs.ztd, D-019)."""
    th, ah = load(sym, "H4", "2024-06-01T0000")
    h4 = [Candle(th[i], ah["open"][i], ah["high"][i], ah["low"][i], ah["close"][i]) for i in range(len(th))]
    close_t = [(datetime.strptime(x, "%Y-%m-%d %H:%M").timestamp() + 4 * 3600) for x in th]
    cache = {}
    out = []
    for s in sigs:
        ok = False
        for z in s.zones:
            tz = datetime.strptime(t[z["start"]], "%Y-%m-%d %H:%M").timestamp()
            n = bisect.bisect_right(close_t, tz)          # velas H4 cerradas al empezar la zona
            if n < HTF_AVG_N + 3:
                continue
            key = (n, s.direction)
            if key not in cache:
                avg = float(np.mean(ah["high"][n - HTF_AVG_N:n] - ah["low"][n - HTF_AVG_N:n]))
                cache[key] = (avg, broken_zones(h4, s.direction, n, avg, ZTD_L, BASE.max_width))
            avg, zones = cache[key]
            buy = s.direction == BUY
            for _, _, hi, lo, _ in zones:
                if (z["high"] < lo) if buy else (z["low"] > hi):
                    continue
                gap = max(0.0, z["low"] - hi) / avg if buy else max(0.0, lo - z["high"]) / avg
                if gap <= ZTD_D:
                    ok = True
                    break
            if ok:
                break
        out.append(ok)
    return out


def account(entries, exits):
    """Plan §8.1 (B): máximo 1 operación abierta; devuelve los índices de las operaciones tomadas."""
    order = np.argsort(entries, kind="stable")
    taken, free_from = [], -1
    for i in order:
        if entries[i] > free_from:
            taken.append(i)
            free_from = exits[i]
    return np.array(taken, dtype=int)


def drawdown(pnl):
    eq = np.cumsum(pnl)
    return float(np.max(np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq)) if len(pnl) else 0.0


def metrics(p, norm, buy_mask):
    if len(p) == 0:
        return {"n": 0}
    win, loss = p[p > 0], p[p <= 0]
    return {"n": int(len(p)), "ganadoras_%": round(100 * len(win) / len(p), 2),
            "beneficio_usd": round(float(win.sum()), 2), "pérdida_usd": round(float(loss.sum()), 2),
            "expectativa_usd": round(float(p.mean()), 4), "expectativa_puntos": round(float(p.mean()) / POINT, 2),
            "expectativa_velas_medias": round(float(norm.mean()), 5),
            "factor_beneficio": round(float(win.sum() / -loss.sum()), 4) if loss.sum() < 0 else None,
            "compras": int(buy_mask.sum()), "ventas": int((~buy_mask).sum()),
            "exp_compras_usd": round(float(p[buy_mask].mean()), 4) if buy_mask.any() else None,
            "exp_ventas_usd": round(float(p[~buy_mask].mean()), 4) if (~buy_mask).any() else None,
            "drawdown_usd": round(drawdown(p), 2)}


def run_job(job):
    sym, tf, part = job
    t, a = load(sym, tf)
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    sp, prudent = spreads(sym, a["spread"])
    lo_t, hi_t = (START, CUT) if part == "dev" else (CUT, END)
    i0 = bisect.bisect_left(t, lo_t)
    i1 = bisect.bisect_right(t, hi_t) - 1                 # última vela de la parte
    last_entry = i1 - EXITS["4velas"]                      # la salida principal debe caer dentro de la parte
    vm = float(np.mean(h[i0:i1 + 1] - l[i0:i1 + 1]))       # vela media de la parte (unidad común, plan §8)

    sigs = [s for s in detect_all(t, a, i1 + 1) if i0 <= s.vela0_index + 1 <= last_entry]
    keep = {"a": [True] * len(sigs),
            "b": ztd_h4(sym, sigs, t, a),
            "c": [any(z["measures"]["F3_close_dist"] <= F3 and z["measures"]["F4_rejection"] <= F4 for z in s.zones)
                  for s in sigs]}
    entry = np.array([s.vela0_index + 1 for s in sigs], dtype=int)
    buy = np.array([s.direction == BUY for s in sigs], dtype=bool)

    def pnl_at(e, x, b, slip=SLIP):
        p = trade_pnl(o, c, sp, e, x, b, slip)
        n = nights_between(t[e], t[x])
        return p + (swap_cost(sym, b, c[x], n) if n else 0.0)

    def r43_exit(s):
        e, lvl = s.vela0_index + 1, s.zones[0]["entry"]
        for x in range(e, e + EXITS["4velas"] + 1):
            if (c[x] <= lvl) if s.direction == BUY else (c[x] >= lvl):
                return x
        return e + EXITS["4velas"]

    res = {"símbolo": sym, "tf": tf, "parte": part, "spread_prudente": prudent, "vela_media": vm,
           "velas": int(i1 - i0 + 1)}
    # Resultado de entrar en cada vela posible (para el control): salida principal, compra y venta
    elig = np.arange(i0, last_entry + 1)
    nights_main = np.array([nights_between(t[e], t[e + 3]) for e in elig])
    base_buy = (c[elig + 3] - SLIP * sp[elig + 3] * POINT) - (o[elig] + (1 + SLIP) * sp[elig] * POINT)
    base_sell = (o[elig] - SLIP * sp[elig] * POINT) - (c[elig + 3] + (1 + SLIP) * sp[elig + 3] * POINT)
    if nights_main.any():
        mode = SPEC[sym][1]
        sw = lambda v: nights_main * (v if mode == 2 else v / 100 * c[elig + 3] / 360)
        base_buy, base_sell = base_buy + sw(SPEC[sym][2]), base_sell + sw(SPEC[sym][3])
    rng = np.random.default_rng([SEED, zlib.crc32(f"{sym}|{tf}|{part}".encode())])   # semilla reproducible

    for v in VARIANTS:
        m = np.array(keep[v], dtype=bool)
        e_v, b_v = entry[m], buy[m]
        sel = [s for s, k in zip(sigs, keep[v]) if k]
        main = np.array([pnl_at(e, e + 3, b) for e, b in zip(e_v, b_v)])
        out = {"A": metrics(main, main / vm, b_v)}
        for name, off in (("mj2", EXITS["mj2"]), ("mj3", EXITS["mj3"])):
            p = np.array([pnl_at(e, e + off, b) for e, b in zip(e_v, b_v)])
            out["A_" + name] = metrics(p, p / vm, b_v)
        p43 = np.array([pnl_at(s.vela0_index + 1, r43_exit(s), s.direction == BUY) for s in sel])
        out["A_r43"] = metrics(p43, p43 / vm, b_v)
        for sl in SLIP_SENS:
            p = np.array([pnl_at(e, e + 3, b, sl) for e, b in zip(e_v, b_v)])
            out[f"A_desliz_{sl}"] = metrics(p, p / vm, b_v)
        taken = account(e_v, e_v + 3)
        pb = main[taken] if len(taken) else np.array([])
        out["B"] = metrics(pb, pb / vm, b_v[taken] if len(taken) else b_v[:0])
        if part == "holdout" and len(pb):      # Monte Carlo del drawdown (plan §4), sobre (B)
            dds = [drawdown(rng.permutation(pb)) for _ in range(REPS)]
            out["B"]["mc_drawdown_mediana"] = round(float(np.median(dds)), 2)
            out["B"]["mc_drawdown_p95"] = round(float(np.percentile(dds, 95)), 2)
        # Control (plan §5 y §8.1): mismas N, mismas compras/ventas, mismas salidas y costes; 1.000 repeticiones
        n, nb = len(e_v), int(b_v.sum())
        ctrlA, ctrlB, ctrlBn = np.zeros(REPS), np.zeros(REPS), np.zeros(REPS)
        if n:
            for r in range(REPS):
                idx = rng.integers(0, len(elig), n)
                dirs = np.zeros(n, dtype=bool)
                dirs[rng.permutation(n)[:nb]] = True
                pr = np.where(dirs, base_buy[idx], base_sell[idx])
                ctrlA[r] = pr.sum() / vm
                tk = account(elig[idx], elig[idx] + 3)
                ctrlB[r], ctrlBn[r] = pr[tk].sum() / vm, len(tk)
        out["sumA_vm"] = float((main / vm).sum())
        out["sumB_vm"] = float((pb / vm).sum())
        out["ctrlA_sum_vm"] = ctrlA.tolist()
        out["ctrlB_sum_vm"] = ctrlB.tolist()
        out["ctrlB_n"] = ctrlBn.tolist()
        res[v] = out
    return res


def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def main():
    part = sys.argv[1]
    assert part in ("dev", "holdout")
    # Cada símbolo+TF se guarda al terminar; al relanzar solo se calcula lo que falta. Orden M15 → M5 → M1;
    # M15 y M5 con 3 procesos, M1 de uno en uno (memoria).
    cache = OUT / part
    cache.mkdir(parents=True, exist_ok=True)
    todo = lambda tf: [(s, tf, part) for s in SPEC if not (cache / f"{s}_{tf}.json").exists()]

    def save(r):
        f = cache / f"{r['símbolo']}_{r['tf']}.json"
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        tmp.replace(f)
        print(f"hecho {r['símbolo']} {r['tf']}", flush=True)

    for tf in ("M15", "M5"):
        with ProcessPoolExecutor(max_workers=3) as ex:
            for r in ex.map(run_job, todo(tf)):
                save(r)
    for job in todo("M1"):
        save(run_job(job))
    results = [json.loads((cache / f"{s}_{tf}.json").read_text(encoding="utf-8")) for s in SPEC for tf in TF_MIN]
    # Pregunta principal (plan §5): por variante y TF, juntando símbolos, en velas medias
    summary, keys, pv = [], [], []
    for v in VARIANTS:
        for tf in TF_MIN:
            rs = [r for r in results if r["tf"] == tf]
            N = sum(r[v]["A"]["n"] for r in rs)
            exp = sum(r[v]["sumA_vm"] for r in rs) / N if N else 0.0
            ctrl = np.sum([r[v]["ctrlA_sum_vm"] for r in rs], axis=0) / N if N else np.zeros(REPS)
            p = float((ctrl >= exp).mean())
            NB = sum(r[v]["B"]["n"] for r in rs)
            expB = sum(r[v]["sumB_vm"] for r in rs) / NB if NB else 0.0
            ctrlB = np.sum([r[v]["ctrlB_sum_vm"] for r in rs], axis=0) / np.maximum(
                np.sum([r[v]["ctrlB_n"] for r in rs], axis=0), 1)
            usd = [r[v]["A"].get("expectativa_usd") for r in rs if r[v]["A"]["n"]]
            summary.append({"variante": v, "tf": tf, "N": N, "expectativa_vm": round(exp, 5),
                            "control_media_vm": round(float(ctrl.mean()), 5),
                            "control_p95_vm": round(float(np.percentile(ctrl, 95)), 5), "p": p,
                            "B_N": NB, "B_expectativa_vm": round(expB, 5),
                            "B_control_media_vm": round(float(ctrlB.mean()), 5),
                            "B_p": float((ctrlB >= expB).mean()),
                            "expectativa_usd_por_símbolo": usd})
            keys.append(len(summary) - 1)
            pv.append(p)
    for i, a in zip(keys, holm(pv)):
        s = summary[i]
        s["p_holm"] = a
        s["supera_al_control"] = bool(s["expectativa_vm"] > 0 and a < 0.05)
    for r in results:   # las listas de control no hacen falta en el archivo
        for v in VARIANTS:
            for k in ("ctrlA_sum_vm", "ctrlB_sum_vm", "ctrlB_n"):
                r[v].pop(k)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{part}.json").write_text(json.dumps({"plan": "docs/BACKTEST_PLAN.md", "resumen": summary,
                                                  "detalle": results}, indent=1, ensure_ascii=False),
                                      encoding="utf-8")
    for s in summary:
        print(f"{s['variante']} {s['tf']:<4} N {s['N']:>7}  exp {s['expectativa_vm']:+.5f} vm  control "
              f"{s['control_media_vm']:+.5f} (p95 {s['control_p95_vm']:+.5f})  p {s['p']:.3f} holm {s['p_holm']:.3f}"
              f"  → {'SUPERA' if s['supera_al_control'] else 'no supera'} | B N {s['B_N']} exp {s['B_expectativa_vm']:+.5f}"
              f" control {s['B_control_media_vm']:+.5f} p {s['B_p']:.3f}")


if __name__ == "__main__":
    main()

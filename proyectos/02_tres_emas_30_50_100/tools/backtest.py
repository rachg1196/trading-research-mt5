"""Backtest de la fase 3 (docs/BACKTEST_PLAN.md). Solo datos descargados; MT5 no se toca.

Uso:
  python tools\\backtest.py desarrollo                     parte de desarrollo (antes del corte)
  python tools\\backtest.py reserva --autorizo-reserva     reserva: UNA sola vez, con orden expresa

Qué hace, por símbolo × temporalidad (series "ok" del manifiesto):
- Prueba principal (valores por defecto) y variantes V1-V5 (solo informativas), con el detector de
  emas/detector.py. Entrada en la apertura de C+1, salida en el cierre de C+4, una operación abierta a
  la vez (P-14). Sensibilidad de la principal: retraso de 1 y 3 velas (P-15) y deslizamiento 0 × y 1 ×.
- Costes (§5): spread de cada vela (spread 0 -> el de la especificación, D-018; si la mediana del
  historial < 80 % de la especificación, el mayor de los dos), deslizamiento 0,5 × spread en entrada y
  salida, swap por medianoche del servidor (swap triple el día que da MT5) y comisión de
  analysis/backtest/costes_mt5.json (0 si no hay datos).
- Control aleatorio (§6): mismas N, mismas compras y ventas, misma salida y costes, una abierta a la
  vez, 1.000 repeticiones con semilla fija. Control secundario solo para la principal.
- Comparación por temporalidad (§7) con Holm; Monte Carlo del drawdown (§8).
Reutiliza solo la parte estadística genérica de importado/backtest_anterior.py (sin rsr_srs).
"""
import argparse
import json
import pickle
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from emas.detector import Params, detectar  # noqa: E402
from emas.indicators import ema, vela_media  # noqa: E402

HIST = RAIZ / "analysis" / "mt5" / "history"
MANIFIESTO = RAIZ / "analysis" / "backtest" / "manifiesto.json"
COSTES = RAIZ / "analysis" / "backtest" / "costes_mt5.json"
SALIDA = RAIZ / "analysis" / "backtest"
BLOQUEO = SALIDA / "RESERVA_USADA.txt"

TFS = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30", "H1", "H2", "H3", "H4"]
REPS = 1000
DESLIZ, DESLIZ_SENS = 0.5, (0.0, 1.0)
RETRASOS = (1, 3)
VELAS_SALIDA = 3                     # salida = entrada + 3 = confirmación + 4 (U-4)
MIN_OPS_TF, MIN_OPS_COMB, ALFA = 100, 30, 0.05
CONFIGS = {
    "principal": Params(),
    "V1": Params(ruptura="mecha"),
    "V2": Params(separacion=0.0),
    "V3": Params(tolerancia_toque=0.1),
    "V4": Params(solo_primer_retroceso=False),
    "V5": Params(alineadas_todo_el_patron=False),
}
COLUMNAS = ["tiempo", "entrada", "salida", "compra", "vm", "puntos", "usd", "spread_vm", "desliz_vm", "swap_vm"]


# --- Cálculos genéricos (con pruebas en tests/test_backtest.py) -----------

def spread_efectivo(bruto, espec, mediana):
    """Spread en puntos por vela (§5, D-018). Devuelve (spread, se_uso_el_prudente)."""
    sp = np.where(np.asarray(bruto, dtype=float) <= 0, espec, bruto).astype(float)
    prudente = bool(mediana < 0.8 * espec)
    return (np.maximum(sp, espec) if prudente else sp), prudente


def noches(dia, e, x, dia_triple):
    """Medianoches del servidor entre la apertura de e y el cierre de x (días ordinales de las velas).
    Las que empiezan en el día del swap triple (MT5: 0 = domingo ... 6 = sábado) cuentan 3."""
    resto = (dia_triple % 7)            # ordinal % 7: 0 = domingo, 1 = lunes, ..., 5 = viernes
    antes = lambda d: (d - resto + 6) // 7   # cuántos días k < d tienen k % 7 == resto
    de, dx = np.asarray(dia)[e], np.asarray(dia)[x]
    return (dx - de) + 2 * (antes(dx) - antes(de))


def resultado(o, c, sp, punto, e, x, compra, desliz, swap_noche, n_noches):
    """Resultado en precio de entrar en la apertura de e y salir en el cierre de x (velas bid).
    Compra: entra a apertura + spread + desliz., sale a cierre − desliz.
    Venta: entra a apertura − desliz., sale a cierre + spread + desliz.
    swap_noche: swap por noche en precio (negativo = coste). Devuelve (neto, spread, desliz., swap)
    con los costes en positivo."""
    bruto = np.where(compra, c[x] - o[e], o[e] - c[x])
    c_spread = np.where(compra, sp[e], sp[x]) * punto
    c_desliz = desliz * (sp[e] + sp[x]) * punto
    c_swap = -swap_noche * n_noches
    return bruto - c_spread - c_desliz - c_swap, c_spread, c_desliz, c_swap


def una_a_la_vez(entradas, salidas):
    """P-14: índices de las operaciones tomadas (las que llegan con otra abierta se ignoran)."""
    tomadas, libre = [], -1
    for i in np.argsort(entradas, kind="stable"):
        if entradas[i] > libre:
            tomadas.append(i)
            libre = salidas[i]
    return np.array(tomadas, dtype=int)


def control(rng, n, n_compras, vm_compra, vm_venta, pool_compra, pool_venta, reps=REPS):
    """Control aleatorio: por repetición, n entradas al azar (n_compras compras, de pool_compra; el
    resto ventas, de pool_venta), salida a +3 velas, una abierta a la vez. vm_compra/vm_venta: resultado
    en VM de entrar en cada vela. Devuelve (suma_vm, operaciones) de cada repetición."""
    suma, cuenta = np.zeros(reps), np.zeros(reps, dtype=int)
    n_ventas = n - n_compras
    if n == 0:
        return suma, cuenta
    if (n_compras and not len(pool_compra)) or (n_ventas and not len(pool_venta)):
        return np.full(reps, np.nan), cuenta
    e = np.concatenate([pool_compra[rng.integers(0, max(len(pool_compra), 1), (reps, n_compras))],
                        pool_venta[rng.integers(0, max(len(pool_venta), 1), (reps, n_ventas))]], axis=1)
    es_compra = np.concatenate([np.ones((reps, n_compras), bool), np.zeros((reps, n_ventas), bool)], axis=1)
    orden = np.argsort(e, axis=1, kind="stable")
    e, es_compra = np.take_along_axis(e, orden, 1), np.take_along_axis(es_compra, orden, 1)
    libre = np.full(reps, -1)
    for j in range(n):
        ej = e[:, j]
        ok = ej > libre
        suma += np.where(ok, np.where(es_compra[:, j], vm_compra[ej], vm_venta[ej]), 0.0)
        cuenta += ok
        libre = np.where(ok, ej + VELAS_SALIDA, libre)
    return suma, cuenta


def holm(pvals):
    orden = sorted(range(len(pvals)), key=lambda i: pvals[i])
    ajust, acumulado = [0.0] * len(pvals), 0.0
    for rango, i in enumerate(orden):
        acumulado = max(acumulado, min(1.0, (len(pvals) - rango) * pvals[i]))
        ajust[i] = acumulado
    return ajust


def drawdown(valores):
    eq = np.cumsum(valores)
    return float(np.max(np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq)) if len(valores) else 0.0


# --- Una serie (símbolo × temporalidad) -----------------------------------

def procesar(trabajo):
    serie, espec, parte, costes = trabajo
    sym, tf = serie["simbolo"], serie["tf"]
    df = pd.read_csv(HIST / serie["archivo"])
    tiempos = pd.to_datetime(df["time"])
    en_desarrollo = (tiempos < pd.Timestamp(serie["corte_reserva"])).to_numpy()
    if parte == "desarrollo":
        df, tiempos = df[en_desarrollo].reset_index(drop=True), tiempos[en_desarrollo].reset_index(drop=True)
        i0 = 0
    else:
        i0 = int(en_desarrollo.sum())   # la reserva usa el desarrollo como calentamiento
    n = len(df)
    ultima = n - 1
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    punto = float(espec["point"])
    usd_por_precio = float(espec["trade_tick_value"]) / float(espec["trade_tick_size"])
    sp, prudente = spread_efectivo(df["spread"].to_numpy(float), float(espec["spread"]),
                                   float(serie["calidad"]["spread_mediana_puntos"]))
    dia = tiempos.to_numpy().astype("datetime64[D]").astype(np.int64) + 719163   # ordinal de date
    t_ns = tiempos.to_numpy().astype("datetime64[ns]").astype(np.int64)
    vm = vela_media(h, l)
    comision = costes["comision_por_lote"]
    comision = float(comision.get(sym, 0.0)) if isinstance(comision, dict) else 0.0
    dia_triple = costes["swap_triple_dia"].get(sym, 3)
    if dia_triple is None:
        dia_triple = 3

    def swap_noche(compra, x):
        v = np.where(compra, float(espec["swap_long"]), float(espec["swap_short"]))
        modo = int(espec["swap_mode"])
        if modo == 2:   # dinero por lote y noche
            return v / usd_por_precio
        if modo == 5:   # interés anual % sobre el precio actual
            return v / 100 * c[x] / 360 * float(espec["trade_contract_size"])
        if modo == 0:
            return np.zeros_like(v)
        raise ValueError(f"modo de swap {modo} no previsto ({sym})")

    def evaluar(e, x, compra, desliz=DESLIZ):
        neto, c_sp, c_de, c_sw = resultado(o, c, sp, punto, e, x, compra, desliz, swap_noche(compra, x),
                                          noches(dia, e, x, dia_triple))
        neto = neto - comision / usd_por_precio
        u = vm[e - 1]   # vela media de la vela de confirmación (la anterior a la entrada)
        return {"tiempo": t_ns[e], "entrada": e, "salida": x, "compra": compra, "vm": neto / u, "puntos": neto / punto,
                "usd": neto * usd_por_precio, "spread_vm": c_sp / u, "desliz_vm": c_de / u,
                "swap_vm": c_sw / u}

    def operaciones(senales, retraso=0):
        e = np.array([s.vela_confirmacion + 1 + retraso for s in senales], dtype=int)
        x = np.array([s.vela_confirmacion + 4 for s in senales], dtype=int)
        compra = np.array([s.direccion == "compra" for s in senales], dtype=bool)
        dentro = (e >= max(i0, 1)) & (x <= ultima)    # ninguna operación cruza el corte
        e, x, compra = e[dentro], x[dentro], compra[dentro]
        k = una_a_la_vez(e, x)
        return (e[k], x[k], compra[k]) if len(k) else (e[:0], x[:0], compra[:0])

    # Resultado de entrar en cada vela válida (para el control).
    lo, hi = max(i0, 501), ultima - VELAS_SALIDA
    todas = np.arange(lo, hi + 1) if hi >= lo else np.array([], dtype=int)
    vm_c, vm_v = np.full(n, np.nan), np.full(n, np.nan)
    if len(todas):
        vm_c[todas] = evaluar(todas, todas + VELAS_SALIDA, np.ones(len(todas), bool))["vm"]
        vm_v[todas] = evaluar(todas, todas + VELAS_SALIDA, np.zeros(len(todas), bool))["vm"]
    e30, e50, e100 = ema(c, 30), ema(c, 50), ema(c, 100)
    sep = 0.25 * vm
    alc = (e100 < e50) & (e50 < e30) & ((e30 - e50) >= sep) & ((e50 - e100) >= sep)
    baj = (e100 > e50) & (e50 > e30) & ((e50 - e30) >= sep) & ((e100 - e50) >= sep)
    pool_c2 = todas[alc[todas - 1]] if len(todas) else todas
    pool_v2 = todas[baj[todas - 1]] if len(todas) else todas

    res = {"simbolo": sym, "tf": tf, "parte": parte, "velas": n - i0, "spread_prudente": prudente,
           "velas_validas_control": int(len(todas)), "configs": {}}
    for nombre, params in CONFIGS.items():
        senales = detectar(df, params)
        e, x, compra = operaciones(senales)
        ops = evaluar(e, x, compra)
        rng = np.random.default_rng([20261019, zlib.crc32(f"{sym}|{tf}|{parte}|{nombre}".encode())])
        suma, cuenta = control(rng, len(e), int(compra.sum()), vm_c, vm_v, todas, todas)
        r = {"senales": len(senales), "ops": ops, "ctrl_suma": suma, "ctrl_n": cuenta}
        if nombre == "principal":
            suma2, cuenta2 = control(rng, len(e), int(compra.sum()), vm_c, vm_v, pool_c2, pool_v2)
            r.update(ctrl2_suma=suma2, ctrl2_n=cuenta2, sens={})
            for d in RETRASOS:
                r["sens"][f"retraso_{d}"] = evaluar(*operaciones(senales, d))
            for s in DESLIZ_SENS:
                r["sens"][f"desliz_{s:g}"] = evaluar(e, x, compra, s)
        res["configs"][nombre] = r
    return res


# --- Agregación ------------------------------------------------------------

def tabla(series, config, clave="ops"):
    filas = []
    for r in series:
        d = r["configs"][config][clave] if clave == "ops" else r["configs"][config]["sens"][clave]
        if len(d["entrada"]):
            f = pd.DataFrame({k: np.asarray(d[k]) for k in COLUMNAS})
            f["simbolo"], f["tf"] = r["simbolo"], r["tf"]
            filas.append(f)
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame(columns=COLUMNAS + ["simbolo", "tf"])


def metricas(d):
    """Métricas (§8). El drawdown sigue el orden real de las entradas (todas las series juntas)."""
    if len(d) == 0:
        return {"n": 0}
    v = d["vm"].to_numpy()
    orden = np.argsort(d["tiempo"].to_numpy(), kind="stable")
    gan, per = v[v > 0].sum(), v[v <= 0].sum()
    return {"n": int(len(v)), "compras": int(d["compra"].sum()), "ventas": int((~d["compra"]).sum()),
            "ganadoras_pct": round(100 * float((v > 0).mean()), 2),
            "exp_vm": round(float(v.mean()), 5), "exp_puntos": round(float(d["puntos"].mean()), 2),
            "exp_usd_lote": round(float(d["usd"].mean()), 4),
            "beneficio_bruto_vm": round(float(gan), 3), "perdida_bruta_vm": round(float(per), 3),
            "factor_beneficio": round(float(gan / -per), 4) if per < 0 else None,
            "drawdown_max_vm": round(drawdown(v[orden]), 3),
            "drawdown_max_usd": round(drawdown(d["usd"].to_numpy()[orden]), 2),
            "coste_spread_vm": round(float(d["spread_vm"].mean()), 5),
            "coste_desliz_vm": round(float(d["desliz_vm"].mean()), 5),
            "coste_swap_vm": round(float(d["swap_vm"].mean()), 5)}


def comparar(series, config, tf, ctrl="ctrl"):
    """Expectativa (VM) de la estrategia en la TF, frente a la del control (todas las series juntas)."""
    rs = [r for r in series if r["tf"] == tf]
    ops = [np.asarray(r["configs"][config]["ops"]["vm"]) for r in rs]
    v = np.concatenate(ops) if ops else np.array([])
    if not len(v):
        return {"n": 0, "exp_vm": None, "ctrl_exp_vm": None, "p": 1.0}
    suma = np.sum([r["configs"][config][f"{ctrl}_suma"] for r in rs], axis=0)
    cuenta = np.sum([r["configs"][config][f"{ctrl}_n"] for r in rs], axis=0)
    medias = suma / np.maximum(cuenta, 1)
    exp = float(v.mean())
    return {"n": int(len(v)), "exp_vm": round(exp, 5), "ctrl_exp_vm": round(float(np.nanmean(medias)), 5),
            "ctrl_p95_vm": round(float(np.nanpercentile(medias, 95)), 5),
            "p": float(np.mean(np.nan_to_num(medias, nan=np.inf) >= exp))}


def agregar(series, parte, manifiesto):
    resumen = {"parte": parte, "fecha": datetime.now().isoformat(timespec="seconds"),
               "series": len(series), "configs": {}}
    filas_tf = []
    for config in CONFIGS:
        comps = {tf: comparar(series, config, tf) for tf in TFS}
        resumen["configs"][config] = comps
    # Holm: 15 comparaciones para la principal; 75 para las variantes juntas (§7).
    p_ajust = dict(zip(TFS, holm([resumen["configs"]["principal"][tf]["p"] for tf in TFS])))
    for tf in TFS:
        resumen["configs"]["principal"][tf]["p_holm"] = p_ajust[tf]
    claves = [(v, tf) for v in CONFIGS if v != "principal" for tf in TFS]
    for (v, tf), p in zip(claves, holm([resumen["configs"][v][tf]["p"] for v, tf in claves])):
        resumen["configs"][v][tf]["p_holm"] = p
    for config in CONFIGS:
        for tf in TFS:
            cmp_ = resumen["configs"][config][tf]
            cmp_["supera"] = bool(cmp_["n"] >= MIN_OPS_TF and (cmp_["exp_vm"] or 0) > 0
                                  and cmp_["p_holm"] < ALFA)
            cmp_["estado"] = ("datos insuficientes" if cmp_["n"] < MIN_OPS_TF
                              else "supera" if cmp_["supera"] else "no supera")

    # Control secundario (principal) y sensibilidad.
    for tf in TFS:
        resumen["configs"]["principal"][tf]["control_secundario"] = comparar(series, "principal", tf, "ctrl2")
    sens = {}
    for clave in [f"retraso_{d}" for d in RETRASOS] + [f"desliz_{s:g}" for s in DESLIZ_SENS]:
        t = tabla(series, "principal", clave)
        sens[clave] = {tf: metricas(t[t["tf"] == tf]) for tf in TFS}
    resumen["sensibilidad_principal"] = sens

    # Métricas completas por TF (principal y variantes), Monte Carlo y combinaciones.
    rng = np.random.default_rng(manifiesto["semillas"]["montecarlo"])
    filas_comb = []
    for config in CONFIGS:
        t = tabla(series, config)
        for tf in TFS:
            d = t[t["tf"] == tf]
            m = metricas(d)
            fila = {"config": config, "tf": tf, **m, **{k: resumen["configs"][config][tf].get(k) for k in
                    ("ctrl_exp_vm", "ctrl_p95_vm", "p", "p_holm", "estado")}}
            if config == "principal" and len(d):
                v, u = d["vm"].to_numpy(), d["usd"].to_numpy()
                dd = [(drawdown(v[k]), drawdown(u[k])) for k in (rng.permutation(len(v)) for _ in range(REPS))]
                dd = np.array(dd)
                fila.update(mc_dd_mediana_vm=round(float(np.median(dd[:, 0])), 3),
                            mc_dd_p95_vm=round(float(np.percentile(dd[:, 0], 95)), 3),
                            mc_dd_mediana_usd=round(float(np.median(dd[:, 1])), 2),
                            mc_dd_p95_usd=round(float(np.percentile(dd[:, 1], 95)), 2))
            filas_tf.append(fila)
            if config == "principal":
                for (sym, compra), g in d.groupby(["simbolo", "compra"]):
                    base = {"simbolo": sym, "tf": tf, "direccion": "compra" if compra else "venta", "n": len(g)}
                    filas_comb.append({**base, **(metricas(g) if len(g) >= MIN_OPS_COMB
                                                  else {"estado": "insuficiente"})})
    return resumen, pd.DataFrame(filas_tf), pd.DataFrame(filas_comb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parte", choices=["desarrollo", "reserva"])
    ap.add_argument("--autorizo-reserva", action="store_true")
    ap.add_argument("--procesos", type=int, default=12)
    args = ap.parse_args()
    if args.parte == "reserva":
        if not args.autorizo_reserva:
            sys.exit("La reserva solo se procesa con orden expresa (--autorizo-reserva).")
        if BLOQUEO.exists():
            sys.exit(f"La reserva ya se evaluó ({BLOQUEO.read_text(encoding='utf-8').strip()}). Bloqueado.")
        BLOQUEO.write_text(f"Reserva evaluada el {datetime.now().isoformat(timespec='seconds')}\n",
                           encoding="utf-8")

    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    costes = json.loads(COSTES.read_text(encoding="utf-8"))
    carpeta = SALIDA / args.parte / "series"
    carpeta.mkdir(parents=True, exist_ok=True)
    validas = [s for s in manifiesto["series"] if s["estado"] == "ok"]
    archivo = lambda s: carpeta / f"{s['simbolo'].replace(' ', '')}_{s['tf']}.pkl"
    pendientes = sorted((s for s in validas if not archivo(s).exists()),
                        key=lambda s: -s["velas_desarrollo"])
    trabajos = [(s, manifiesto["simbolos"][s["simbolo"]], args.parte, costes) for s in pendientes]
    print(f"{len(validas)} series, {len(trabajos)} pendientes", flush=True)
    with ProcessPoolExecutor(args.procesos) as ex:
        for k, r in enumerate(ex.map(procesar, trabajos), 1):
            with archivo({"simbolo": r["simbolo"], "tf": r["tf"]}).open("wb") as f:
                pickle.dump(r, f)
            if k % 25 == 0 or k == len(trabajos):
                print(f"  {k}/{len(trabajos)}", flush=True)

    series = []
    for s in validas:
        with archivo(s).open("rb") as f:
            series.append(pickle.load(f))
    resumen, por_tf, comb = agregar(series, args.parte, manifiesto)
    resumen["spread_prudente"] = sorted({r["simbolo"] for r in series if r["spread_prudente"]})
    resumen["comision"] = costes["comision_por_lote"]
    (SALIDA / f"resumen_{args.parte}.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False),
                                                       encoding="utf-8")
    por_tf.to_csv(SALIDA / f"por_tf_{args.parte}.csv", sep=";", index=False, encoding="utf-8-sig")
    comb.to_csv(SALIDA / f"combinaciones_{args.parte}.csv", sep=";", index=False, encoding="utf-8-sig")
    cols = ["config", "tf", "n", "exp_vm", "ctrl_exp_vm", "p", "p_holm", "estado"]
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(por_tf[cols].to_string(index=False))


if __name__ == "__main__":
    main()

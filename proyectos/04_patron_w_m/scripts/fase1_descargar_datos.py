# -*- coding: utf-8 -*-
"""
FASE 1 - Descarga de historico (SOLO LECTURA).
- Mercados: BreakX 600, TrendX 600, SwitchX 600
- Las 21 temporalidades de MT5
- Incluye el spread de cada vela + una muestra de ticks para medir el spread real
- Separa el ultimo 25% del tiempo como RESERVA (datos\\reserva), que no se usa hasta la Fase 7
Este script NO envia, modifica ni cierra ordenes.
"""
import os
import sys
import json
import time
import datetime as dt

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(BASE, "datos", "historico")
RESV = os.path.join(BASE, "datos", "reserva")
RES = os.path.join(BASE, "resultados")
for d in (HIST, RESV, RES):
    os.makedirs(d, exist_ok=True)

SIMBOLOS = ["BreakX 600", "TrendX 600", "SwitchX 600"]
TFS = {
    "M1": mt5.TIMEFRAME_M1, "M2": mt5.TIMEFRAME_M2, "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4, "M5": mt5.TIMEFRAME_M5, "M6": mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10, "M12": mt5.TIMEFRAME_M12, "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20, "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2, "H3": mt5.TIMEFRAME_H3, "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6, "H8": mt5.TIMEFRAME_H8, "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1,
}
FRACCION_RESERVA = 0.25
INICIO_BUSQUEDA = dt.datetime(2018, 1, 1)

try:
    import pyarrow  # noqa
    EXT = "parquet"
except ImportError:
    EXT = "csv.gz"

lineas = []
def log(m=""):
    print(m, flush=True)
    lineas.append(str(m))

def guardar_df(df, ruta_sin_ext):
    ruta = f"{ruta_sin_ext}.{EXT}"
    if EXT == "parquet":
        df.to_parquet(ruta, index=False)
    else:
        df.to_csv(ruta, index=False, compression="gzip")
    return ruta

def nombre_archivo(sym):
    return sym.replace(" ", "_")

def descargar(sym, tf_const):
    """Descarga por bloques mensuales desde INICIO_BUSQUEDA hasta ahora."""
    # calentamiento: obliga al terminal a sincronizar la serie
    mt5.copy_rates_from_pos(sym, tf_const, 0, 10)
    time.sleep(0.2)
    ahora = dt.datetime.now() + dt.timedelta(days=2)
    partes = []
    ini = INICIO_BUSQUEDA
    while ini < ahora:
        fin = min(ini + dt.timedelta(days=31), ahora)
        r = mt5.copy_rates_range(sym, tf_const, ini, fin)
        if r is not None and len(r) > 0:
            partes.append(pd.DataFrame(r))
        ini = fin
    if not partes:
        return None
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    df["time"] = pd.to_datetime(df["time"], unit="s")  # hora del servidor
    return df[["time", "open", "high", "low", "close", "tick_volume", "spread"]]

def muestra_ticks(sym, dias=3):
    fin = dt.datetime.now() + dt.timedelta(days=1)
    ini = fin - dt.timedelta(days=dias + 1)
    t = mt5.copy_ticks_range(sym, ini, fin, mt5.COPY_TICKS_INFO)
    if t is None or len(t) == 0:
        return None
    t = pd.DataFrame(t)
    t = t[(t["bid"] > 0) & (t["ask"] > 0)]
    return t

log(f"FASE 1 - {dt.datetime.now():%Y-%m-%d %H:%M:%S}  (formato: {EXT})")
if not mt5.initialize():
    log(f"ERROR: no se pudo conectar con MT5: {mt5.last_error()}")
    open(os.path.join(RES, "fase1_reporte.txt"), "w", encoding="utf-8").write("\n".join(lineas))
    sys.exit(1)

resumen = []
cortes = {}
for sym in SIMBOLOS:
    log("")
    log(f"=== {sym} ===")
    if not mt5.symbol_select(sym, True):
        log(f"  No se pudo seleccionar {sym}: {mt5.last_error()}")
        continue
    info = mt5.symbol_info(sym)
    punto = info.point

    # 1) M1 define el rango de tiempo y el corte de reserva (igual para todas las temporalidades)
    datos = {}
    for tf_nombre, tf_const in TFS.items():
        df = descargar(sym, tf_const)
        if df is None or df.empty:
            log(f"  {tf_nombre:<4}: sin datos ({mt5.last_error()})")
            continue
        datos[tf_nombre] = df
        log(f"  {tf_nombre:<4}: {len(df):>9,} velas  {df['time'].iloc[0]:%Y-%m-%d} -> {df['time'].iloc[-1]:%Y-%m-%d %H:%M}")

    if "M1" not in datos:
        log("  Sin M1: se omite el simbolo.")
        continue
    t0 = datos["M1"]["time"].iloc[0]
    t1 = datos["M1"]["time"].iloc[-1]
    corte = t0 + (t1 - t0) * (1 - FRACCION_RESERVA)
    corte = corte.floor("D")  # el corte cae a medianoche (hora servidor)
    cortes[sym] = {"inicio": str(t0), "corte_reserva": str(corte), "fin": str(t1)}
    log(f"  Rango M1: {t0} -> {t1}  |  corte reserva: {corte}")

    carpeta_h = os.path.join(HIST, nombre_archivo(sym))
    carpeta_r = os.path.join(RESV, nombre_archivo(sym))
    os.makedirs(carpeta_h, exist_ok=True)
    os.makedirs(carpeta_r, exist_ok=True)

    for tf_nombre, df in datos.items():
        dev = df[df["time"] < corte]
        res = df[df["time"] >= corte]
        guardar_df(dev, os.path.join(carpeta_h, tf_nombre))
        guardar_df(res, os.path.join(carpeta_r, tf_nombre))
        sp = dev["spread"]
        resumen.append({
            "simbolo": sym, "tf": tf_nombre,
            "velas_desarrollo": len(dev), "velas_reserva": len(res),
            "desde": dev["time"].iloc[0] if len(dev) else None,
            "corte_reserva": corte,
            "hasta": df["time"].iloc[-1],
            "spread_velas_mediana_pts": float(sp.median()) if len(sp) else None,
            "spread_velas_p90_pts": float(sp.quantile(0.9)) if len(sp) else None,
            "punto": punto,
        })

    # 2) spread real a partir de ticks recientes
    t = muestra_ticks(sym)
    if t is not None and len(t):
        s = (t["ask"] - t["bid"]) / punto
        cortes[sym]["spread_ticks_pts"] = {
            "n_ticks": int(len(s)), "mediana": float(s.median()),
            "media": float(s.mean()), "p90": float(s.quantile(0.9)),
            "max": float(s.max()),
        }
        log(f"  Spread real (ticks recientes, {len(s):,}): mediana={s.median():.0f} pts  p90={s.quantile(0.9):.0f} pts  max={s.max():.0f} pts")
    else:
        log("  No se pudieron leer ticks para el spread real.")

mt5.shutdown()

pd.DataFrame(resumen).to_csv(os.path.join(RES, "fase1_resumen.csv"), index=False, encoding="utf-8-sig")
with open(os.path.join(RES, "fase1_cortes.json"), "w", encoding="utf-8") as f:
    json.dump({"formato": EXT, "fraccion_reserva": FRACCION_RESERVA,
               "hora": "servidor MT5", "simbolos": cortes}, f, indent=2, ensure_ascii=False)
log("")
log("FASE 1 terminada. Ninguna orden fue enviada ni modificada.")
open(os.path.join(RES, "fase1_reporte.txt"), "w", encoding="utf-8").write("\n".join(lineas))

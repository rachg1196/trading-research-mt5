"""
Fase 1 - Descarga de datos de BreakX 600 desde MetaTrader 5.

SOLO LECTURA: este script únicamente lee velas, ticks e información del símbolo.
No contiene ninguna función que envíe, modifique o cierre órdenes
(no usa order_send, order_check, ni positions/orders).

Uso:
  1. Abre MetaTrader 5 (con la sesión iniciada, real o demo; da igual, solo lee).
  2. En una terminal (cmd) dentro de esta carpeta:
        pip install MetaTrader5 pandas
        python descargar_datos.py
  3. Los datos quedan en la carpeta 04_datos (al lado de esta carpeta de scripts).
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import MetaTrader5 as mt5

SIMBOLO = "BreakX 600"
TEMPORALIDADES = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
}
DIAS_TICKS = 60          # días recientes de ticks para medir el spread real (bid/ask)
BLOQUE = 50_000          # velas por petición

BASE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(os.path.dirname(BASE), "04_datos")
os.makedirs(SALIDA, exist_ok=True)


def log(msg):
    print(msg, flush=True)


def descargar_velas(nombre, tf):
    """Descarga todas las velas disponibles, hacia atrás en bloques."""
    partes = []
    pos = 0
    while True:
        r = mt5.copy_rates_from_pos(SIMBOLO, tf, pos, BLOQUE)
        if r is None or len(r) == 0:
            break
        partes.append(pd.DataFrame(r))
        if len(r) < BLOQUE:
            break
        pos += BLOQUE
    if not partes:
        log(f"  {nombre}: sin datos ({mt5.last_error()})")
        return None
    df = pd.concat(partes).drop_duplicates("time").sort_values("time")
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.rename(columns={"spread": "spread_pts"})
    ruta = os.path.join(SALIDA, f"BreakX600_{nombre}.csv")
    df.to_csv(ruta, index=False)
    log(f"  {nombre}: {len(df):,} velas  {df.time.min()}  ->  {df.time.max()}")
    return {"velas": int(len(df)), "desde": str(df.time.min()), "hasta": str(df.time.max())}


def descargar_ticks(punto):
    """Ticks de los últimos DIAS_TICKS días, día por día. Guarda spread por minuto."""
    fin = datetime.now(timezone.utc) + timedelta(days=1)
    ini = fin - timedelta(days=DIAS_TICKS + 1)
    resumen = []
    d = ini
    while d < fin:
        t = mt5.copy_ticks_range(SIMBOLO, d, d + timedelta(days=1), mt5.COPY_TICKS_INFO)
        if t is not None and len(t) > 0:
            df = pd.DataFrame(t)
            df = df[(df.bid > 0) & (df.ask > 0)]
            if len(df):
                df["time"] = pd.to_datetime(df["time_msc"], unit="ms")
                df["spread_pts"] = (df.ask - df.bid) / punto
                m = df.set_index("time").resample("1min").agg(
                    bid=("bid", "last"), ask=("ask", "last"),
                    spread_media=("spread_pts", "mean"),
                    spread_max=("spread_pts", "max"),
                    ticks=("spread_pts", "size"))
                resumen.append(m.dropna())
        d += timedelta(days=1)
    if not resumen:
        log(f"  Ticks: sin datos ({mt5.last_error()})")
        return None
    m = pd.concat(resumen)
    ruta = os.path.join(SALIDA, "BreakX600_spread_por_minuto_ticks.csv")
    m.to_csv(ruta)
    log(f"  Ticks: {int(m.ticks.sum()):,} ticks resumidos en {len(m):,} minutos "
        f"| spread medio {m.spread_media.mean():.0f} pts")
    return {"minutos": int(len(m)), "desde": str(m.index.min()), "hasta": str(m.index.max()),
            "spread_medio_pts": round(float(m.spread_media.mean()), 1)}


def main():
    if not mt5.initialize():
        log(f"No se pudo conectar con MetaTrader 5: {mt5.last_error()}")
        log("Asegúrate de que MT5 esté abierto y vuelve a intentarlo.")
        sys.exit(1)
    try:
        if not mt5.symbol_select(SIMBOLO, True):
            log(f"El símbolo '{SIMBOLO}' no está disponible: {mt5.last_error()}")
            sys.exit(1)
        info = mt5.symbol_info(SIMBOLO)
        punto = info.point
        datos_simbolo = {
            "simbolo": SIMBOLO, "digitos": info.digits, "punto": punto,
            "valor_tick": info.trade_tick_value, "tamano_tick": info.trade_tick_size,
            "contrato": info.trade_contract_size, "lote_min": info.volume_min,
            "lote_paso": info.volume_step, "stops_level": info.trade_stops_level,
            "spread_actual_pts": info.spread, "spread_flotante": info.spread_float,
        }
        log(f"Símbolo {SIMBOLO}: punto={punto}, dígitos={info.digits}, "
            f"spread actual={info.spread} pts")

        resultado = {"descargado": datetime.now().isoformat(timespec="seconds"),
                     "simbolo": datos_simbolo, "velas": {}}
        log("Descargando velas...")
        for nombre, tf in TEMPORALIDADES.items():
            resultado["velas"][nombre] = descargar_velas(nombre, tf)
        log(f"Descargando ticks de los últimos {DIAS_TICKS} días (puede tardar)...")
        resultado["ticks"] = descargar_ticks(punto)

        with open(os.path.join(SALIDA, "resumen_descarga.json"), "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        log(f"\nListo. Archivos en: {SALIDA}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()

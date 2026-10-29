# -*- coding: utf-8 -*-
"""Descarga ticks reales (bid/ask) de los ultimos 30 dias. SOLO LECTURA."""
import os, sys, time
from datetime import datetime, timedelta, timezone
import pandas as pd
import MetaTrader5 as mt5
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(BASE, "datos", "ticks"); os.makedirs(DST, exist_ok=True)
RUTA = r"C:\Program Files\MT5 Weltrade\terminal64.exe"
ok = mt5.initialize(path=RUTA) if os.path.exists(RUTA) else mt5.initialize()
if not ok: print("ERROR", mt5.last_error()); sys.exit(1)
fin = datetime.now(timezone.utc) + timedelta(hours=3)
ini = fin - timedelta(days=30)
for s in ["BreakX 600", "TrendX 600", "SwitchX 600", "BreakX 1200", "SwitchX 1200", "TrendX 1200"]:
    mt5.symbol_select(s, True); partes = []; t = ini; t0 = time.time()
    while t < fin:
        t2 = min(t + timedelta(days=2), fin)
        r = mt5.copy_ticks_range(s, t, t2, mt5.COPY_TICKS_ALL)
        if r is not None and len(r): partes.append(pd.DataFrame(r)[["time_msc", "bid", "ask"]])
        t = t2
    if not partes: print(s, "sin ticks", mt5.last_error()); continue
    df = pd.concat(partes).drop_duplicates()
    df.to_csv(os.path.join(DST, s.replace(" ", "") + "_ticks.csv.gz"), index=False, compression="gzip")
    print(f"{s}: {len(df)} ticks {pd.to_datetime(df.time_msc.iloc[0], unit='ms')} -> {pd.to_datetime(df.time_msc.iloc[-1], unit='ms')} ({time.time()-t0:.0f}s)", flush=True)
mt5.shutdown(); print("Terminado. No se envio ni modifico ninguna orden.")

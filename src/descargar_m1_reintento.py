# -*- coding: utf-8 -*-
"""Descarga SOLO M1 (las demas temporalidades se arman desde M1; verificado identico a MT5).
Lee la lista de simbolos de resultados/lista_descarga.txt (uno por linea). Salta los que ya existen. SOLO LECTURA."""
import os, sys, time, json
from datetime import datetime, timezone
import pandas as pd
import MetaTrader5 as mt5
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "resultados"); DST = os.path.join(BASE, "datos", "completo"); os.makedirs(DST, exist_ok=True)
RUTA = r"C:\Program Files\MT5 Weltrade\terminal64.exe"
lista = [x.strip() for x in open(os.path.join(RES, "lista_descarga.txt"), encoding="utf-8") if x.strip()]
ok = mt5.initialize(path=RUTA) if os.path.exists(RUTA) else mt5.initialize()
if not ok:
    print("ERROR al conectar:", mt5.last_error()); sys.exit(1)
log = {}
for i, s in enumerate(lista, 1):
    ruta = os.path.join(DST, f"{s}_M1.csv.gz")
    if os.path.exists(ruta):
        print(f"[{i}/{len(lista)}] {s}: ya existe, se salta"); continue
    t0 = time.time(); print(f"[{i}/{len(lista)}] {s} M1: descargando...", flush=True)
    mt5.symbol_select(s, True)
    r = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_M1, 0, 6_000_000)
    if r is None or len(r) < 2:   # reintentos: por fecha y con menos velas
        print("    primer intento fallo:", mt5.last_error(), "-> reintento por fechas", flush=True)
        r = mt5.copy_rates_range(s, mt5.TIMEFRAME_M1, datetime(2016, 1, 1, tzinfo=timezone.utc), datetime.now(timezone.utc))
    if r is None or len(r) < 2:
        r = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_M1, 0, 1_500_000)
    if r is None or len(r) < 2:
        print("    ERROR sin datos:", mt5.last_error()); log[s] = {"error": str(mt5.last_error())}; continue
    df = pd.DataFrame(r).iloc[:-1]
    tmp = ruta + ".tmp"; df.to_csv(tmp, index=False, compression="gzip"); os.replace(tmp, ruta)
    f0 = datetime.fromtimestamp(int(df.time.iloc[0]), timezone.utc); f1 = datetime.fromtimestamp(int(df.time.iloc[-1]), timezone.utc)
    log[s] = {"velas": len(df), "desde": str(f0), "hasta": str(f1)}
    print(f"    {len(df)} velas {f0:%Y-%m-%d} -> {f1:%Y-%m-%d %H:%M} ({time.time()-t0:.0f} s)", flush=True)
    json.dump(log, open(os.path.join(RES, "descarga_m1_reintento_log.json"), "w"), indent=1)
mt5.shutdown()
print("Descarga terminada. No se envio ni modifico ninguna orden.")

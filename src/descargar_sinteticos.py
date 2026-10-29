# -*- coding: utf-8 -*-
"""Descarga M1 de los sinteticos TrendX / SwitchX / BreakX (y sus especificaciones). SOLO LECTURA."""
import os, sys, json, time
import pandas as pd
import MetaTrader5 as mt5
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "resultados"); DST = os.path.join(BASE, "datos", "sinteticos"); os.makedirs(DST, exist_ok=True)
RUTA = r"C:\Program Files\MT5 Weltrade\terminal64.exe"
ok = mt5.initialize(path=RUTA) if os.path.exists(RUTA) else mt5.initialize()
if not ok:
    print("ERROR al conectar:", mt5.last_error()); sys.exit(1)
acc = mt5.account_info()
print("Cuenta:", acc.login, acc.server, "modo", acc.trade_mode, "(0=demo)")
todos = mt5.symbols_get()
sel = [s.name for s in todos if any(k in s.name.upper() for k in ("TRENDX", "SWITCHX", "BREAKX"))]
print("Mercados encontrados:", sel)
specs = {}
for s in sel:
    mt5.symbol_select(s, True); time.sleep(0.3)
    i = mt5.symbol_info(s)
    specs[s] = dict(point=i.point, digits=i.digits, spread=i.spread, spread_float=i.spread_float,
                    contract=i.trade_contract_size, vmin=i.volume_min, vstep=i.volume_step,
                    tick_value=i.trade_tick_value, tick_size=i.trade_tick_size, swap_mode=i.swap_mode,
                    swap_long=i.swap_long, swap_short=i.swap_short, swap3=i.swap_rollover3days,
                    stops_level=i.trade_stops_level, trade_mode=i.trade_mode, bid=i.bid, ask=i.ask)
    nombre = s.replace(" ", "")
    t0 = time.time()
    r = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_M1, 0, 3_000_000)
    if r is None or len(r) < 2:
        print(s, "ERROR sin datos", mt5.last_error()); continue
    df = pd.DataFrame(r).iloc[:-1]
    df.to_csv(os.path.join(DST, f"{nombre}_M1.csv.gz"), index=False, compression="gzip")
    print(f"{s}: {len(df)} velas {pd.to_datetime(df.time.iloc[0], unit='s')} -> {pd.to_datetime(df.time.iloc[-1], unit='s')} "
          f"spread {i.spread} ({time.time()-t0:.0f}s)", flush=True)
json.dump(specs, open(os.path.join(RES, "specs_sinteticos.json"), "w"), indent=1)
mt5.shutdown()
print("Terminado. No se envio ni modifico ninguna orden.")

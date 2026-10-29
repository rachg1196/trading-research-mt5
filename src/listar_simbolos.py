# -*- coding: utf-8 -*-
"""Lista TODOS los simbolos de Weltrade con su grupo, si se pueden operar y sus costes. SOLO LECTURA."""
import json, os, sys, time
import MetaTrader5 as mt5
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "resultados"); os.makedirs(RES, exist_ok=True)
RUTA = r"C:\Program Files\MT5 Weltrade\terminal64.exe"
ok = mt5.initialize(path=RUTA) if os.path.exists(RUTA) else mt5.initialize()
if not ok:
    print("ERROR al conectar:", mt5.last_error()); sys.exit(1)
modos = {0: "deshabilitado", 1: "solo compras", 2: "solo ventas", 3: "solo cerrar", 4: "completo"}
out = {}
todos = mt5.symbols_get() or []
print(f"Simbolos totales: {len(todos)}")
for s in todos:
    mt5.symbol_select(s.name, True)
time.sleep(3)   # dar tiempo a que lleguen precios
for s in todos:
    si = mt5.symbol_info(s.name)
    d = {c: getattr(si, c, None) for c in ["name", "description", "path", "digits", "point", "trade_contract_size",
         "trade_tick_size", "trade_tick_value", "volume_min", "volume_step", "spread", "swap_mode", "swap_long",
         "swap_short", "swap_rollover3days", "trade_stops_level", "trade_mode", "trade_calc_mode", "currency_base",
         "currency_profit", "currency_margin", "bid", "ask"]}
    d["modo"] = modos.get(si.trade_mode, si.trade_mode)
    try:
        d["margen_lote_min"] = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, s.name, si.volume_min, si.ask) if si.ask else None
        d["valor_1pct_lote_min"] = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, s.name, si.volume_min, si.ask, si.ask * 1.01) if si.ask else None
    except Exception as e:
        d["margen_lote_min"] = str(e)
    out[s.name] = d
mt5.shutdown()
json.dump(out, open(os.path.join(RES, "simbolos_weltrade.json"), "w", encoding="utf-8"), indent=1, default=str)
grupos = {}
for n, d in out.items():
    g = (d["path"] or "").split("\\")[0]
    grupos.setdefault(g, []).append(f"{n}({d['modo']})")
with open(os.path.join(RES, "simbolos_weltrade.txt"), "w", encoding="utf-8") as f:
    for g, l in grupos.items():
        line = f"{g} [{len(l)}]: " + ", ".join(l)
        print(line); f.write(line + "\n")
print("Lectura terminada. No se envio ni modifico ninguna orden.")

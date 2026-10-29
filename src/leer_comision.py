# -*- coding: utf-8 -*-
"""Lee (SOLO LECTURA) posiciones abiertas y operaciones del historial para ver la comision.
No envia, modifica ni cierra ordenes."""
import json, os, sys
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "resultados"); os.makedirs(RES, exist_ok=True)
RUTA = r"C:\Program Files\MT5 Weltrade\terminal64.exe"
lineas, datos = [], {}
def out(t=""):
    print(t); lineas.append(str(t))

ok = mt5.initialize(path=RUTA) if os.path.exists(RUTA) else mt5.initialize()
if not ok:
    out(f"ERROR al conectar: {mt5.last_error()}"); sys.exit(1)
try:
    pos = mt5.positions_get() or []
    out(f"Posiciones abiertas: {len(pos)}")
    datos["posiciones"] = []
    for p in pos:
        d = p._asdict(); datos["posiciones"].append(d)
        out(f"  {p.symbol} {'COMPRA' if p.type == 0 else 'VENTA'} {p.volume} lotes a {p.price_open}; precio actual {p.price_current};"
            f" resultado {p.profit} USD; swap {p.swap}")
    desde = datetime.now(timezone.utc) - timedelta(days=60)
    hasta = datetime.now(timezone.utc) + timedelta(days=2)
    deals = mt5.history_deals_get(desde, hasta) or []
    out(f"Operaciones (deals) ultimos 60 dias: {len(deals)}")
    datos["deals"] = []
    entradas = {0: "ENTRADA", 1: "SALIDA", 2: "REVERSO", 3: "SALIDA POR"}
    for d in deals:
        dd = d._asdict(); datos["deals"].append(dd)
        if d.symbol:
            out(f"  {datetime.fromtimestamp(d.time, timezone.utc):%Y-%m-%d %H:%M} (hora servidor) {d.symbol}"
                f" {entradas.get(d.entry, d.entry)} {d.volume} lotes a {d.price}: comision {d.commission}, fee {d.fee},"
                f" swap {d.swap}, resultado {d.profit}")
    out("Lectura terminada. No se envio ni modifico ninguna orden.")
finally:
    mt5.shutdown()
    open(os.path.join(RES, "comision.txt"), "w", encoding="utf-8").write("\n".join(lineas) + "\n")
    json.dump(datos, open(os.path.join(RES, "comision.json"), "w", encoding="utf-8"), indent=2, default=str)

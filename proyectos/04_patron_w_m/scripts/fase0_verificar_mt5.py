# -*- coding: utf-8 -*-
"""
FASE 0 - Verificacion de conexion con MT5 (SOLO LECTURA).
Este script NO envia, modifica ni cierra ordenes. No usa order_send ni nada parecido.
Solo lee: info del terminal, info de la cuenta (tipo real/demo) y lista de simbolos.
Resultados en: ..\\resultados\\
"""
import os
import sys
import csv
import datetime as dt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "resultados")
os.makedirs(RES, exist_ok=True)
LOG = os.path.join(RES, "fase0_reporte.txt")

lineas = []
def log(msg=""):
    print(msg)
    lineas.append(str(msg))

def guardar():
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

log(f"FASE 0 - {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
log(f"Python: {sys.version.split()[0]}  ({sys.executable})")

try:
    import MetaTrader5 as mt5
except ImportError:
    log("ERROR: falta el paquete MetaTrader5 (pip install MetaTrader5)")
    guardar()
    sys.exit(1)

log(f"Paquete MetaTrader5: {mt5.__version__}")

if not mt5.initialize():
    log(f"ERROR: no se pudo conectar con MT5: {mt5.last_error()}")
    log("Verifica que MetaTrader 5 este abierto.")
    guardar()
    sys.exit(1)

ti = mt5.terminal_info()
ai = mt5.account_info()
log("")
log("=== TERMINAL ===")
log(f"Nombre: {ti.name} | Compania: {ti.company} | Build: {mt5.version()}")
log(f"Conectado al servidor: {ti.connected} | Trading algoritmico permitido: {ti.trade_allowed}")
log(f"Max barras en grafico (ajuste del terminal): {ti.maxbars}")

log("")
log("=== CUENTA (solo lectura) ===")
if ai is not None:
    modos = {0: "DEMO", 1: "CONCURSO", 2: "REAL"}
    log(f"Servidor: {ai.server} | Tipo: {modos.get(ai.trade_mode, ai.trade_mode)} | Moneda: {ai.currency}")
    log(f"Apalancamiento: 1:{ai.leverage}")
else:
    log("No se pudo leer la cuenta.")

symbols = mt5.symbols_get()
log("")
log(f"=== SIMBOLOS DISPONIBLES: {len(symbols)} ===")

filas = []
for s in symbols:
    filas.append({
        "simbolo": s.name,
        "ruta": s.path,
        "descripcion": s.description,
        "digitos": s.digits,
        "punto": s.point,
        "spread_actual": s.spread,
        "spread_flotante": s.spread_float,
        "lote_min": s.volume_min,
        "valor_tick": s.trade_tick_value,
        "tamano_tick": s.trade_tick_size,
        "visible_en_market_watch": s.visible,
    })

csv_path = os.path.join(RES, "fase0_simbolos.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(filas[0].keys()) if filas else ["simbolo"])
    w.writeheader()
    w.writerows(filas)

# agrupar por carpeta (ruta) para mostrar ordenado
grupos = {}
for r in filas:
    g = r["ruta"].rsplit("\\", 1)[0] if "\\" in r["ruta"] else "(sin grupo)"
    grupos.setdefault(g, []).append(r)
for g in sorted(grupos):
    log(f"\n[{g}]  ({len(grupos[g])})")
    for r in sorted(grupos[g], key=lambda x: x["simbolo"]):
        log(f"  {r['simbolo']:<28} spread={r['spread_actual']:<6} digitos={r['digitos']}  {r['descripcion']}")

# chequeo de los sinteticos de interes y de acceso a historico
log("")
log("=== CHEQUEO SINTETICOS PRINCIPALES ===")
nombres = [r["simbolo"] for r in filas]
for clave in ["BreakX 600", "FlipX 1", "TrendX 600"]:
    k = clave.lower().replace(" ", "")
    match = [n for n in nombres if k in n.lower().replace(" ", "")]
    if not match:
        log(f"  {clave}: NO encontrado")
        continue
    for n in match:
        mt5.symbol_select(n, True)
        rates = mt5.copy_rates_from_pos(n, mt5.TIMEFRAME_M1, 0, 1000)
        if rates is None or len(rates) == 0:
            log(f"  {n}: encontrado, pero sin historico M1 ({mt5.last_error()})")
        else:
            ini = dt.datetime.utcfromtimestamp(int(rates[0]['time']))
            fin = dt.datetime.utcfromtimestamp(int(rates[-1]['time']))
            log(f"  {n}: OK - lectura de prueba {len(rates)} velas M1 ({ini:%Y-%m-%d %H:%M} -> {fin:%Y-%m-%d %H:%M})")

mt5.shutdown()
log("")
log("FASE 0 terminada. Ninguna orden fue enviada ni modificada.")
guardar()

"""
Script de diagnóstico para verificar la conexión con MetaTrader 5,
la cuenta DEMO y las especificaciones del símbolo BreakX 600.
"""

import sys
import json
from pathlib import Path
import MetaTrader5 as mt5

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

def test():
    print("=" * 65)
    print("DIAGNÓSTICO DE CONEXIÓN CON METATRADER 5 — BREAKX 600")
    print("=" * 65)
    
    if not CONFIG_PATH.exists():
        print(f"ERROR: config.json no encontrado en {CONFIG_PATH}")
        return
        
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    print(f"Modo configurado en config.json: {cfg.get('ACCOUNT_TYPE')}")
    print(f"Símbolo objetivo               : {cfg.get('SYMBOL')}")
    print(f"Lotaje fijo                    : {cfg.get('LOT_SIZE')}")
    print(f"Take Profit configurado        : {cfg.get('TP_POINTS')} pts")
    print(f"Stop Loss configurado          : {cfg.get('SL_POINTS')} pts")
    print()
    
    login = int(cfg.get("ACCOUNT_LOGIN", 0))
    password = str(cfg.get("ACCOUNT_PASSWORD", ""))
    server = str(cfg.get("ACCOUNT_SERVER", ""))
    
    if login > 0 and password and server:
        init_ok = mt5.initialize(login=login, password=password, server=server)
    else:
        init_ok = mt5.initialize()
        
    if not init_ok:
        print(f"❌ Error al inicializar MT5. Asegúrate de tener la terminal MT5 abierta.")
        print(f"   Código de error: {mt5.last_error()}")
        return
        
    acc = mt5.account_info()
    if acc is None:
        print(f"❌ No se pudo leer la información de la cuenta.")
        mt5.shutdown()
        return
        
    print(f"✅ Conectado a terminal MT5:")
    print(f"   - Servidor    : {acc.server}")
    print(f"   - Nombre      : {acc.name}")
    print(f"   - Balance     : {acc.balance:.2f} {acc.currency}")
    print(f"   - Equidad     : {acc.equity:.2f} {acc.currency}")
    print(f"   - Margen libre: {acc.margin_free:.2f} {acc.currency}")
    print(f"   - Trade Demo  : {'SÍ' if acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else 'REAL / OTRO'}")
    print()
    
    symbol = cfg.get("SYMBOL", "BreakX 600")
    if not mt5.symbol_select(symbol, True):
        print(f"❌ No se pudo seleccionar '{symbol}'. Verifica que el broker tenga este símbolo activo.")
        mt5.shutdown()
        return
        
    s_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    
    print(f"✅ Símbolo '{symbol}' disponible en el broker:")
    print(f"   - Dígitos     : {s_info.digits}")
    print(f"   - Point       : {s_info.point}")
    print(f"   - Lote mínimo : {s_info.volume_min}")
    print(f"   - Lote máximo : {s_info.volume_max}")
    print(f"   - Paso de lote: {s_info.volume_step}")
    if tick:
        spread_pts = round((tick.ask - tick.bid) / s_info.point)
        print(f"   - Bid actual  : {tick.bid:.2f}")
        print(f"   - Ask actual  : {tick.ask:.2f}")
        print(f"   - Spread      : {spread_pts} puntos ({tick.ask - tick.bid:.2f} en precio)")
    print()
    print("Todo listo para operar en cuenta DEMO con bot_breakx600.py.")
    print("=" * 65)
    mt5.shutdown()

if __name__ == "__main__":
    test()

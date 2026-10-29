"""Costes del backtest leídos de MT5 en SOLO LECTURA (BACKTEST_PLAN §5): comisión y día de swap triple.

- Comisión: se busca en el historial de operaciones de la cuenta (history_deals_get). Si no hay
  operaciones con comisión de los símbolos sintéticos, se anota "sin datos" (el backtest supone 0).
- Swap: día de la semana del swap triple (swap_rollover3days) de cada símbolo del manifiesto.
No envía órdenes ni cambia nada. No guarda login, nombre ni saldo.
Uso:  python tools\\mt5_costes.py "C:\\Program Files\\MT5 Weltrade\\terminal64.exe"
Salida: analysis/backtest/costes_mt5.json
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5

RAIZ = Path(__file__).resolve().parent.parent
MANIFIESTO = RAIZ / "analysis" / "backtest" / "manifiesto.json"
SALIDA = RAIZ / "analysis" / "backtest" / "costes_mt5.json"


def main():
    ok = mt5.initialize(path=sys.argv[1]) if len(sys.argv) > 1 else mt5.initialize()
    if not ok:
        sys.exit(f"initialize falló: {mt5.last_error()}")
    try:
        simbolos = list(json.loads(MANIFIESTO.read_text(encoding="utf-8"))["simbolos"])
        acc = mt5.account_info()
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now()) or ()
        propios = [d for d in deals if d.symbol in simbolos]
        comision = {}
        for d in propios:
            if d.volume > 0:
                comision.setdefault(d.symbol, []).append(d.commission / d.volume)
        r = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "servidor": acc.server if acc else None,
            "cuenta_demo": bool(acc and acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO),
            "operaciones_en_historial": len(deals),
            "operaciones_de_sinteticos": len(propios),
            "comision_por_lote": {s: sum(v) / len(v) for s, v in comision.items()} or "sin datos",
            "swap_triple_dia": {},
        }
        for s in simbolos:
            info = mt5.symbol_info(s)
            r["swap_triple_dia"][s] = None if info is None else info.swap_rollover3days
        SALIDA.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: v for k, v in r.items() if k != "swap_triple_dia"}, indent=2, ensure_ascii=False))
        print("swap triple (0=domingo ... 6=sábado):", sorted(set(r["swap_triple_dia"].values()), key=str))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()

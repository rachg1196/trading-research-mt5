"""Descarga de historial en SOLO LECTURA para los casos de prueba (D-014). Sin órdenes.

Uso:  python tools\\mt5_history.py "<terminal64.exe>" "<símbolo>" <TF> <desde> <hasta>
      fechas en hora del servidor, formato 2025-06-14T03:30
Única acción que modifica MT5: symbol_select si el símbolo no está en Market Watch (autorizado en D-014).
Salida: analysis/mt5/history/<símbolo>_<TF>_<desde>_<hasta>.csv (time en hora del servidor).
"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

OUT = Path(__file__).resolve().parent.parent / "analysis" / "mt5" / "history"


def main():
    term, sym, tf, t0, t1 = sys.argv[1:6]
    if not mt5.initialize(path=term):
        sys.exit(f"initialize falló: {mt5.last_error()}")
    try:
        info = mt5.symbol_info(sym)
        if info is None:
            sys.exit(f"{sym}: no existe en el servidor")
        if not info.visible and not mt5.symbol_select(sym, True):
            sys.exit(f"{sym}: symbol_select falló: {mt5.last_error()}")
        # copy_rates_range interpreta las fechas como UTC; las velas de MT5 llevan la hora del servidor
        a, b = (datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in (t0, t1))
        r = mt5.copy_rates_range(sym, getattr(mt5, f"TIMEFRAME_{tf}"), a, b)
        if r is None or not len(r):
            first = mt5.copy_rates_from_pos(sym, getattr(mt5, f"TIMEFRAME_{tf}"), 0, 1)
            sys.exit(f"{sym} {tf}: sin velas en {t0}..{t1} ({mt5.last_error()}); "
                     f"vela más reciente: {None if first is None else datetime.utcfromtimestamp(int(first[0]['time']))}")
        OUT.mkdir(parents=True, exist_ok=True)
        f = OUT / f"{sym.replace(' ', '')}_{tf}_{t0.replace(':', '')}_{t1.replace(':', '')}.csv"
        with f.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "open", "high", "low", "close", "tick_volume", "spread"])
            for x in r:
                w.writerow([datetime.fromtimestamp(int(x["time"]), timezone.utc).strftime("%Y-%m-%d %H:%M"),
                            x["open"], x["high"], x["low"], x["close"], x["tick_volume"], x["spread"]])
        print(f"{f.name}: {len(r)} velas")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()

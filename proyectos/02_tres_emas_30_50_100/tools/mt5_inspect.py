"""T13: inspección de MT5 en SOLO LECTURA (sin órdenes, sin symbol_select, sin cambiar nada).

Uso:  python tools\\mt5_inspect.py "C:\\Program Files\\MT5 Weltrade\\terminal64.exe"
Salida: analysis/mt5/<servidor>_symbols.csv y <servidor>_report.json. No guarda login, nombre ni saldo.
"""
import csv
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5

OUT = Path(__file__).resolve().parent.parent / "analysis" / "mt5"
TFS = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30",
       "H1", "H2", "H3", "H4", "H6", "H8", "H12"]
SYM_FIELDS = ["name", "description", "path", "visible", "select", "trade_mode", "trade_exemode",
              "filling_mode", "order_mode", "trade_calc_mode", "volume_min", "volume_max",
              "volume_step", "volume_limit", "digits", "point", "spread", "spread_float",
              "trade_tick_size", "trade_tick_value", "trade_contract_size", "currency_profit",
              "swap_mode", "swap_long", "swap_short", "trade_stops_level", "trade_freeze_level"]
WATCH = re.compile(r"break|fx ?vol|flip", re.I)  # símbolos que nombra el usuario (FR-05)


def enum_names(prefix):
    return {getattr(mt5, n): n for n in dir(mt5) if n.startswith(prefix)}


def main():
    ok = mt5.initialize(path=sys.argv[1]) if len(sys.argv) > 1 else mt5.initialize()
    if not ok:
        sys.exit(f"initialize falló: {mt5.last_error()}")
    try:
        term, acc = mt5.terminal_info(), mt5.account_info()
        server = acc.server if acc else "sin_cuenta"
        rep = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "paquete": mt5.__version__, "terminal_version": mt5.version(),
            "terminal": {k: getattr(term, k) for k in
                         ("name", "company", "path", "connected", "trade_allowed", "tradeapi_disabled")},
            "cuenta": None if acc is None else {
                "server": acc.server, "company": acc.company, "currency": acc.currency,
                "trade_mode": enum_names("ACCOUNT_TRADE_MODE_").get(acc.trade_mode, acc.trade_mode),
                "margin_mode": enum_names("ACCOUNT_MARGIN_MODE_").get(acc.margin_mode, acc.margin_mode),
                "trade_allowed": acc.trade_allowed, "trade_expert": acc.trade_expert},
            "tf_constantes": {tf: hasattr(mt5, f"TIMEFRAME_{tf}") for tf in TFS},
        }
        syms = mt5.symbols_get() or ()
        tmode = enum_names("SYMBOL_TRADE_MODE_")
        OUT.mkdir(parents=True, exist_ok=True)
        tag = re.sub(r"[^\w.-]", "_", server)
        with (OUT / f"{tag}_symbols.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(SYM_FIELDS)
            for s in syms:
                w.writerow([tmode.get(s.trade_mode, s.trade_mode) if k == "trade_mode" else getattr(s, k)
                            for k in SYM_FIELDS])
        rep["simbolos_total"] = len(syms)
        rep["simbolos_visibles"] = sum(s.visible for s in syms)
        rep["por_trade_mode"] = {}
        for s in syms:
            k = tmode.get(s.trade_mode, str(s.trade_mode))
            rep["por_trade_mode"][k] = rep["por_trade_mode"].get(k, 0) + 1
        rep["simbolos_usuario"] = [{k: getattr(s, k) for k in ("name", "visible", "trade_mode",
                                    "volume_min", "volume_max", "volume_step", "digits", "point")}
                                   for s in syms if WATCH.search(s.name)]
        # Datos por TF solo en símbolos ya visibles (copy_rates no debe añadir nada a Market Watch).
        probe = [s.name for s in syms if s.visible and WATCH.search(s.name)][:3]
        rep["velas_por_tf"] = {}
        for name in probe:
            rep["velas_por_tf"][name] = {}
            for tf in TFS:
                r = mt5.copy_rates_from_pos(name, getattr(mt5, f"TIMEFRAME_{tf}"), 0, 5)
                rep["velas_por_tf"][name][tf] = (
                    {"n": len(r), "ultima_apertura": int(r[-1]["time"]), "campos": list(r.dtype.names)}
                    if r is not None and len(r) else str(mt5.last_error()))
        deals = mt5.history_deals_get(datetime.now() - timedelta(days=30), datetime.now() + timedelta(days=1))
        rep["historial_30d"] = {"deals": 0 if deals is None else len(deals),
                                "campos": list(deals[0]._asdict()) if deals else []}
        rep["api_graficos_abiertos"] = [n for n in dir(mt5) if "chart" in n.lower()]
        (OUT / f"{tag}_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str),
                                                encoding="utf-8")
        print(json.dumps(rep, indent=2, ensure_ascii=False, default=str))
    finally:
        mt5.shutdown()  # cierra solo la conexión de Python, no el terminal


if __name__ == "__main__":
    main()

"""Crea analysis/backtest/manifiesto.json (BACKTEST_PLAN §2-§3). NO ejecuta el detector.

Lee los CSV de tools/mt5_history.py y, por símbolo y temporalidad, anota: número de velas, fecha
inicial y final, comprobaciones de calidad y la fecha de corte desarrollo/reserva (70/30), calculada
solo con las fechas de las velas. Añade las semillas fijas y la especificación de cada símbolo.

Uso:  python tools\\manifiesto.py
"""
import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
HIST = RAIZ / "analysis" / "mt5" / "history"
SIMBOLOS = RAIZ / "analysis" / "mt5" / "Weltrade-Demo_symbols.csv"
SALIDA = RAIZ / "analysis" / "backtest" / "manifiesto.json"

SERVIDOR = "Weltrade-Demo"
DESDE, HASTA = "2000-01-01T00:00", "2026-10-18T23:59"   # fin = última vela antes del 19-10-2026 00:00
TFS = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M6": 6, "M10": 10, "M12": 12, "M15": 15,
       "M20": 20, "M30": 30, "H1": 60, "H2": 120, "H3": 180, "H4": 240}
CALENTAMIENTO = 500
FRACCION_DESARROLLO = 0.70
SEMILLAS = {"control_aleatorio": 20261019, "montecarlo": 20261020, "imagenes_validacion": 20261021}
ESPEC = ["description", "digits", "point", "spread", "trade_tick_size", "trade_tick_value",
         "trade_contract_size", "volume_min", "volume_max", "volume_step", "swap_mode", "swap_long",
         "swap_short"]


def fecha_corte(t_util, t_fin):
    """70 % del tiempo entre el inicio útil y el fin, redondeado a las 00:00 de ese día."""
    t = t_util + (t_fin - t_util) * FRACCION_DESARROLLO
    return t.replace(hour=0, minute=0, second=0, microsecond=0)


def revisar(df, minutos):
    t = pd.to_datetime(df["time"])
    paso = t.diff().dropna()
    return {
        "velas_repetidas": int(t.duplicated().sum()),
        "fuera_de_orden": int((paso <= pd.Timedelta(0)).sum()),
        "maximo_menor_que_minimo": int((df["high"] < df["low"]).sum()),
        "ohlc_fuera_de_rango": int(((df["open"] > df["high"]) | (df["open"] < df["low"]) |
                                    (df["close"] > df["high"]) | (df["close"] < df["low"])).sum()),
        "spread_cero_pct": round(100 * float((df["spread"] <= 0).mean()), 3),
        "spread_mediana_puntos": float(df["spread"].median()),
        "huecos": int((paso > pd.Timedelta(minutes=minutos)).sum()),
        "hueco_mayor_horas": round(float(paso.max() / pd.Timedelta(hours=1)), 2) if len(paso) else 0.0,
    }


def main():
    with SIMBOLOS.open(encoding="utf-8") as f:
        espec = {r["name"]: r for r in csv.DictReader(f) if r["path"].startswith("Synthetics\\")}
    series, faltan = [], []
    for nombre in espec:
        for tf, minutos in TFS.items():
            archivo = HIST / f"{nombre.replace(' ', '')}_{tf}_{DESDE.replace(':', '')}_{HASTA.replace(':', '')}.csv"
            if not archivo.exists():
                faltan.append(f"{nombre} {tf}")
                continue
            df = pd.read_csv(archivo)
            fila = {"simbolo": nombre, "tf": tf, "archivo": archivo.name, "velas": len(df),
                    "primera_vela": df["time"].iloc[0], "ultima_vela": df["time"].iloc[-1],
                    "calidad": revisar(df, minutos)}
            if len(df) <= CALENTAMIENTO:
                fila["estado"] = "insuficiente (sin velas después del calentamiento)"
            else:
                t_util = datetime.strptime(df["time"].iloc[CALENTAMIENTO], "%Y-%m-%d %H:%M")
                t_fin = datetime.strptime(df["time"].iloc[-1], "%Y-%m-%d %H:%M")
                corte = fecha_corte(t_util, t_fin)
                t = pd.to_datetime(df["time"])
                fila.update({
                    "inicio_util": t_util.strftime("%Y-%m-%d %H:%M"),
                    "corte_reserva": corte.strftime("%Y-%m-%d %H:%M"),
                    "velas_desarrollo": int(((t >= t_util) & (t < corte)).sum()),
                    "velas_reserva": int((t >= corte).sum()),
                    "estado": "ok",
                })
            series.append(fila)

    manifiesto = {
        "creado": datetime.now().isoformat(timespec="seconds"),
        "servidor": SERVIDOR,
        "fuente": "tools/mt5_history.py (solo lectura; symbol_select autorizado en D-016)",
        "rango_pedido": [DESDE, HASTA],
        "regla_corte": "corte = inicio_util + 70 % de (ultima_vela - inicio_util), a las 00:00; "
                       "inicio_util = vela 501 (tras 500 de calentamiento). Reserva = desde el corte.",
        "calentamiento_velas": CALENTAMIENTO,
        "semillas": SEMILLAS,
        "simbolos": {n: {k: e[k] for k in ESPEC} for n, e in espec.items()},
        "series": series,
        "faltan": faltan,
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{SALIDA}: {len(series)} series, {len(faltan)} faltan")


if __name__ == "__main__":
    main()

"""Paso previo 1.a (BACKTEST_PLAN §1): EMAs propias frente a las de MT5, y OHLC frente a la descarga.

Lee los CSV de mql5/ExportarEMAs.mq5 (analysis/validacion/emas_mt5/) y los históricos descargados.
Calcula las EMAs sobre TODO el historial descargado (igual que el detector) y compara:
  - 10 velas repartidas de forma uniforme en cada archivo (criterio del plan: <= 1 punto);
  - además, todas las velas del archivo (informativo).
No ejecuta el detector.
Uso:  python tools\\comparar_emas.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from emas.indicators import ema  # noqa: E402

MT5 = RAIZ / "analysis" / "validacion" / "emas_mt5"
HIST = RAIZ / "analysis" / "mt5" / "history"
MANIFIESTO = RAIZ / "analysis" / "backtest" / "manifiesto.json"
SALIDA = RAIZ / "analysis" / "validacion" / "comparacion_emas.json"
CASOS = [("FlipX 1", "M1"), ("FX Vol 20", "M15"), ("BreakX 600", "H1")]
TOLERANCIA_PUNTOS = 1.0
VELAS_MUESTRA = 10


def comparar(simbolo, tf, manifiesto):
    serie = next(s for s in manifiesto["series"] if s["simbolo"] == simbolo and s["tf"] == tf)
    punto = float(manifiesto["simbolos"][simbolo]["point"])
    hist = pd.read_csv(HIST / serie["archivo"])
    for n in (30, 50, 100):
        hist[f"ema{n}"] = ema(hist["close"], n)
    hist["time"] = pd.to_datetime(hist["time"])

    mt5 = pd.read_csv(MT5 / f"emas_{simbolo.replace(' ', '')}_{tf}.csv")
    mt5["time"] = pd.to_datetime(mt5["time"], format="%Y.%m.%d %H:%M")
    unidas = mt5.merge(hist, on="time", how="left", suffixes=("_mt5", ""), indicator=True)

    sin_pareja = int((unidas["_merge"] != "both").sum())
    unidas = unidas[unidas["_merge"] == "both"]
    muestra = unidas.iloc[np.linspace(0, len(unidas) - 1, VELAS_MUESTRA).round().astype(int)]
    corte = pd.Timestamp(serie["corte_reserva"])

    def max_dif(df, columnas):
        return {c: round(float((df[f"{c}_mt5"] - df[c]).abs().max() / punto), 6) for c in columnas}

    emas = ["ema30", "ema50", "ema100"]
    ohlc = ["open", "high", "low", "close"]
    r = {
        "simbolo": simbolo, "tf": tf, "punto": punto,
        "velas_mt5": len(mt5), "velas_sin_pareja_en_descarga": sin_pareja,
        "desde": str(mt5["time"].min()), "hasta": str(mt5["time"].max()),
        "todo_en_desarrollo": bool(mt5["time"].max() < corte),
        "muestra_10_velas": [str(t) for t in muestra["time"]],
        "dif_max_puntos_muestra": max_dif(muestra, emas),
        "dif_max_puntos_todas": max_dif(unidas, emas),
        "ohlc_dif_max_puntos_todas": max_dif(unidas, ohlc),
    }
    r["pasa"] = (sin_pareja == 0 and r["todo_en_desarrollo"]
                 and max(r["dif_max_puntos_muestra"].values()) <= TOLERANCIA_PUNTOS)
    return r


def main():
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    resultados = [comparar(s, tf, manifiesto) for s, tf in CASOS]
    SALIDA.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultados, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

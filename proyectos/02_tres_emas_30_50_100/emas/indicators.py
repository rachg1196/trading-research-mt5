"""Indicadores: EMA (igual que MT5) y vela media. Ambos son causales."""
import numpy as np
import pandas as pd

VM_BARS = 20  # vela media: últimas 20 velas cerradas, fijo (STRATEGY_RULES A-7)


def ema(close, n):
    """EMA como el Moving Average exponencial de MT5 (D-013).

    alfa = 2/(n+1); primer valor = primer cierre; después
    ema[i] = cierre[i]*alfa + ema[i-1]*(1-alfa).
    pandas ewm(adjust=False) calcula exactamente esa recursión.
    """
    s = pd.Series(np.asarray(close, dtype=float))
    return s.ewm(span=n, adjust=False).mean().to_numpy()


def vela_media(high, low, n=VM_BARS):
    """Promedio de (máximo - mínimo) de las últimas n velas cerradas, incluida la actual.

    Las primeras n-1 velas no tienen valor (NaN).
    """
    rango = pd.Series(np.asarray(high, dtype=float) - np.asarray(low, dtype=float))
    return rango.rolling(n, min_periods=n).mean().to_numpy()

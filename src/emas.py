# -*- coding: utf-8 -*-
"""Estrategia 3 EMAs (30/50/100) de Raul. Solo velas cerradas. Devuelve senales con la vela de confirmacion.

COMPRA (venta = espejo):
 a. EMAs alineadas: EMA100 < EMA50 < EMA30, separacion entre cada par >= sep * ATR(14) ("armonia"),
    y alineadas al menos MIN_ALINEADAS velas seguidas (no recien cruzadas).
 b. Impulso: se sigue el maximo mas alto desde que empezo la alineacion (o desde el ultimo reinicio).
    Primer retroceso: una vela cuyo minimo toca la EMA30 (o la EMA50). El MAXIMO del impulso es la vela
    con el high mas alto antes de ese toque. Si el retroceso toca la EMA100 -> patron invalido.
 c. ZONA = mecha superior de la vela del maximo: desde max(apertura, cierre) hasta el high.
 d. El precio vuelve a subir y CIERRA por encima de la zona.
 e. Segundo retroceso: la primera vela cuyo minimo toca la zona (<= tope de la zona).
    Si cierra dentro o por encima de la zona -> CONFIRMACION. Si cierra por debajo -> se cancela.
 g. Entrada: apertura de la vela siguiente. Salida: cierre de la 4a vela posterior a la confirmacion.
 Si en cualquier momento se pierde la alineacion o el precio toca la EMA100, se reinicia.
"""
import numpy as np, pandas as pd

MIN_ALINEADAS = 5


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def _buscar(o, h, l, c, e30, e50, e100, a, sep):
    """Busca compras. Para ventas se llama con precios espejados."""
    n = len(c)
    alin = (e100 < e50) & (e50 < e30) & ((e30 - e50) >= sep * a) & ((e50 - e100) >= sep * a)
    racha = np.zeros(n, int)
    for i in range(1, n):
        racha[i] = racha[i - 1] + 1 if alin[i] else 0
    out = []
    estado = 0            # 0 buscando impulso, 1 esperando ruptura de zona, 2 esperando toque de zona
    hi = -np.inf; z_lo = z_hi = 0.0
    for i in range(1, n):
        if racha[i] < MIN_ALINEADAS or l[i] <= e100[i]:
            estado = 0; hi = -np.inf
            continue
        if estado == 0:
            if l[i] <= e30[i] and hi > -np.inf:          # primer retroceso toca EMA30 (o 50)
                estado = 1
            else:
                if h[i] > hi:
                    hi = h[i]; z_lo = max(o[i], c[i]); z_hi = h[i]
            continue
        if estado == 1:
            if c[i] > z_hi:                               # vuelve a subir y cierra arriba de la zona
                estado = 2
            continue
        if estado == 2:
            if l[i] <= z_hi:                              # segundo retroceso toca la zona
                if c[i] >= z_lo:
                    out.append((i, z_lo, z_hi))           # confirmacion en la vela i
                estado = 0; hi = h[i]; z_lo = max(o[i], c[i]); z_hi = h[i]
            continue
    return out


def senales(tfdf, sep):
    o = tfdf.open.to_numpy(float); h = tfdf.high.to_numpy(float); l = tfdf.low.to_numpy(float); c = tfdf.close.to_numpy(float)
    a = atr(h, l, c)
    res = []
    for d, (oo, hh, ll, cc) in [(1, (o, h, l, c)), (-1, (-o, -l, -h, -c))]:
        e30, e50, e100 = ema(cc, 30), ema(cc, 50), ema(cc, 100)
        for i, zl, zh in _buscar(oo, hh, ll, cc, e30, e50, e100, a, sep):
            res.append((d, i))
    s = pd.DataFrame(res, columns=["tipo", "i_conf"]).sort_values("i_conf").reset_index(drop=True)
    s["atr"] = a[s.i_conf.to_numpy()] if len(s) else []
    return s

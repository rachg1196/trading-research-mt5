# -*- coding: utf-8 -*-
"""Tortugas / Donchian (reglas originales, version simple de 1 unidad). Solo velas cerradas para decidir;
las ordenes de ruptura y stop se llenan dentro de la vela (como ordenes stop reales), con salto realista:
si la vela abre ya mas alla del nivel, se llena a la apertura.
  Sistema 1: entra al romper el maximo (compra) / minimo (venta) de 20 velas; sale al romper el de 10 en contra.
  Sistema 2: 55 / 20.
  Stop: 2N desde la entrada (N = ATR de 20 velas, valor de la vela anterior a la entrada).
  Filtro S1: se salta la senal si la anterior del S1 (tomada o no) fue ganadora.
Una posicion a la vez por direccion."""
import numpy as np, pandas as pd


def atr20(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / 20, adjust=False).mean().to_numpy()


def operaciones(tfdf, n_ent, n_sal, dire):
    """Devuelve lista de operaciones (i_ent, p_ent, i_sal, p_sal, motivo) de UNA direccion."""
    o = tfdf.open.to_numpy(float); h = tfdf.high.to_numpy(float); l = tfdf.low.to_numpy(float); c = tfdf.close.to_numpy(float)
    if dire == -1:                       # espejo para ventas
        o, h, l, c = -o, -l, -h, -c
    N = atr20(h, l, c)
    hi_ent = pd.Series(h).rolling(n_ent).max().shift(1).to_numpy()   # maximo de las n velas ANTERIORES
    lo_sal = pd.Series(l).rolling(n_sal).min().shift(1).to_numpy()
    res = []
    n = len(c); i = n_ent + 1
    while i < n:
        lvl = hi_ent[i]
        if np.isnan(lvl) or h[i] <= lvl:
            i += 1; continue
        pe = max(lvl, o[i]); stop = pe - 2 * N[i - 1]
        # misma vela de entrada: solo el stop puede saltar (conservador)
        if l[i] <= stop:
            res.append((i, pe, i, stop, "stop")); i += 1; continue
        j = i + 1; cerrado = False
        while j < n:
            sal = lo_sal[j]
            nivel = max(stop, sal)       # bajando, se toca primero el nivel mas alto
            if l[j] <= nivel:
                ps = min(nivel, o[j])
                res.append((i, pe, j, ps, "stop" if nivel == stop else "canal")); cerrado = True
                break
            j += 1
        if not cerrado:
            break
        i = j + 1
    out = pd.DataFrame(res, columns=["i_ent", "p_ent", "i_sal", "p_sal", "motivo"])
    if dire == -1:
        out["p_ent"] = -out.p_ent; out["p_sal"] = -out.p_sal
    out["tipo"] = dire
    return out


def filtro_s1(ops):
    """Quita la operacion si la anterior (de la misma serie) fue ganadora (antes de costes)."""
    if len(ops) == 0:
        return ops
    gan = ((ops.p_sal - ops.p_ent) * ops.tipo > 0).to_numpy()
    keep = np.r_[True, ~gan[:-1]]
    return ops[keep].reset_index(drop=True)

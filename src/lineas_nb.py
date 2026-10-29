# -*- coding: utf-8 -*-
"""Lineas tipo Joel (ver PLAN_LINEAS_JOEL.md). Version numba. Todo causal: un punto de reaccion en i se
conoce en i+K; ATR usado = el de la vela anterior."""
import numpy as np
from numba import njit

K = 2


@njit(cache=True)
def pivotes(h, l):
    n = len(h); ph = np.zeros(n, np.bool_); pl = np.zeros(n, np.bool_)
    for i in range(K, n - K):
        okh = True; okl = True
        for j in range(i - K, i):
            if h[j] >= h[i]: okh = False
            if l[j] <= l[i]: okl = False
        for j in range(i + 1, i + K + 1):
            if h[j] > h[i]: okh = False
            if l[j] < l[i]: okl = False
        ph[i] = okh; pl[i] = okl
    return ph, pl


@njit(cache=True)
def toques_bajistas(h, l, c, atrp, ph, pl, tol=0.1, prof=1.0, vida=60, maxval=200, maxtoque=6):
    """Devuelve (barra, numero_de_toque, nivel_linea) para lineas bajistas."""
    n = len(h)
    idx = np.nonzero(ph)[0]
    out_i = np.empty(0, np.int64); out_t = np.empty(0, np.int64); out_v = np.empty(0, np.float64)
    bi = []; bt = []; bv = []
    for q in range(len(idx) - 1):
        a = idx[q]; b = idx[q + 1]
        if b - a < 3 or not (h[b] < h[a]): continue
        piso = l[a]
        for j in range(a, b + 1):
            if l[j] < piso: piso = l[j]
        if h[b] - piso < prof * atrp[b] or h[a] - piso < 1.5 * prof * atrp[b]: continue
        m = (h[b] - h[a]) / (b - a)
        start = b + K
        val = -1
        for i in range(start, min(start + maxval, n)):
            L = h[a] + m * (i - a)
            if c[i] > L + tol * atrp[i] or h[i] > h[a]: break
            if c[i] < piso:
                val = i; break
        if val < 0: continue
        num = 3; hay_piso = True; ult = val
        for i in range(val + 1, min(val + vida, n)):
            L = h[a] + m * (i - a)
            if i - K > ult and pl[i - K]: hay_piso = True
            if h[i] >= L - tol * atrp[i] and hay_piso:
                bi.append(i); bt.append(num); bv.append(L - tol * atrp[i])
                ult = i; hay_piso = False; num += 1
                if num > maxtoque: break
            if c[i] > L + tol * atrp[i]: break
    return np.array(bi, np.int64), np.array(bt, np.int64), np.array(bv, np.float64)


@njit(cache=True)
def pierna(h, l, c, ph, pl):
    """Estado al CIERRE de cada vela: +1 alcista / -1 bajista / 0 sin definir."""
    n = len(c); est = np.zeros(n, np.int64)
    ult_h = np.nan; ult_l = np.nan; s = 0
    for i in range(n):
        if i - K >= 0:
            if ph[i - K]: ult_h = h[i - K]
            if pl[i - K]: ult_l = l[i - K]
        if not np.isnan(ult_h) and c[i] > ult_h: s = 1; ult_h = np.nan
        elif not np.isnan(ult_l) and c[i] < ult_l: s = -1; ult_l = np.nan
        est[i] = s
    return est


@njit(cache=True)
def simular(T, O, H, L, S, ent_t0, ent_t1, d, nivel, sl_dist, t_sal, spct, unidades, limite):
    """Una operacion por fila. Si limite: entra en el primer minuto de [ent_t0, ent_t1) que toca el nivel.
    Si no (azar): entra a la apertura del minuto ent_t0. Sale en SL o a la apertura del minuto t_sal.
    Devuelve j_ent, j_sal, pe, ps, spread_usd (j_ent=-1 si no se lleno)."""
    m = len(ent_t0)
    je = np.full(m, -1, np.int64); js = np.full(m, -1, np.int64)
    PE = np.zeros(m); PS = np.zeros(m); SP = np.zeros(m)
    nT = len(T)
    for r in range(m):
        q0 = np.searchsorted(T, ent_t0[r]); q1 = np.searchsorted(T, ent_t1[r])
        j = -1; pe = 0.0
        if limite:
            for q in range(q0, min(q1, nT - 1)):
                if d[r] == -1 and H[q] >= nivel[r]:
                    j = q; pe = max(nivel[r], O[q]); break
                if d[r] == 1 and L[q] <= nivel[r]:
                    j = q; pe = min(nivel[r], O[q]); break
        else:
            if q0 < nT - 1: j = q0; pe = O[q0]
        if j < 0: continue
        b = min(np.searchsorted(T, t_sal[r]), nT - 1)
        if b <= j: b = j + 1
        sl = pe - d[r] * sl_dist[r]
        ps = O[b]; k = b
        for q in range(j, b):
            if (d[r] == 1 and L[q] <= sl) or (d[r] == -1 and H[q] >= sl):
                if q == j: ps = sl
                else: ps = min(sl, O[q]) if d[r] == 1 else max(sl, O[q])
                k = q; break
        je[r] = j; js[r] = k; PE[r] = pe; PS[r] = ps
        SP[r] = max(S[j], spct * pe) * unidades
    return je, js, PE, PS, SP

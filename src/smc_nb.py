# -*- coding: utf-8 -*-
"""Motor SMC estilo LuxAlgo (igual que SMC_EA_LuxAlgo_V2.4 de Raul). Solo velas cerradas: lo que se
calcula en la vela i usa datos hasta i inclusive (la entrada es despues)."""
import numpy as np
from numba import njit


@njit(cache=True)
def atr_sma(h, l, c, n):
    """ATR como en el EA: media simple del TR de las ultimas n velas (hasta i)."""
    m = len(c); out = np.zeros(m); s = 0.0
    tr = np.zeros(m)
    for i in range(m):
        if i == 0: tr[i] = h[i] - l[i]
        else: tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        s += tr[i]
        if i >= n: s -= tr[i - n]
        out[i] = s / min(i + 1, n)
    return out


@njit(cache=True)
def motor(o, h, l, c, size_int=5, size_swing=50, ob_vida=100, fvg_vida=100):
    n = len(c)
    a200 = atr_sma(h, l, c, 200)
    ph = np.empty(n); pl = np.empty(n)
    for i in range(n):
        hv = (h[i] - l[i]) >= 2.0 * a200[i]
        ph[i] = l[i] if hv else h[i]
        pl[i] = h[i] if hv else l[i]
    rint = np.zeros(n, np.int64)      # ruptura interna en la vela i: +1 / -1
    choch = np.zeros(n, np.bool_)     # esa ruptura fue CHoCH
    rsw = np.zeros(n, np.int64)       # ruptura swing
    tsw = np.zeros(n, np.int64)       # tendencia swing al cierre de i
    # eventos de retesteo: vela, direccion, nivel de entrada
    ob_i = []; ob_d = []; ob_v = []
    fv_i = []; fv_d = []; fv_v = []
    # estado pivotes
    legI = -1; legS = -1
    iH = np.nan; iHc = True; iHidx = 0
    iL = np.nan; iLc = True; iLidx = 0
    sH = np.nan; sHc = True
    sL = np.nan; sLc = True
    trI = 0; trS = 0
    # order blocks activos: top, bottom, dir, creado, usado
    obT = np.zeros(200); obB = np.zeros(200); obD = np.zeros(200, np.int64); obC = np.zeros(200, np.int64); nob = 0
    # FVG activos
    fT = np.zeros(400); fB = np.zeros(400); fD = np.zeros(400, np.int64); fC = np.zeros(400, np.int64); nf = 0
    cum = 0.0
    for i in range(n):
        # ---- retesteos (zonas creadas ANTES de esta vela) ----
        k = 0
        while k < nob:
            borrar = False
            if i - obC[k] > ob_vida: borrar = True
            elif obD[k] == 1:
                if l[i] <= obT[k]:
                    ob_i.append(i); ob_d.append(1); ob_v.append(obT[k]); borrar = True
                elif l[i] < obB[k]: borrar = True
            else:
                if h[i] >= obB[k]:
                    ob_i.append(i); ob_d.append(-1); ob_v.append(obB[k]); borrar = True
                elif h[i] > obT[k]: borrar = True
            if borrar:
                obT[k] = obT[nob - 1]; obB[k] = obB[nob - 1]; obD[k] = obD[nob - 1]; obC[k] = obC[nob - 1]; nob -= 1
            else: k += 1
        k = 0
        while k < nf:
            borrar = False
            if i - fC[k] > fvg_vida: borrar = True
            elif fD[k] == 1:
                if l[i] <= fT[k]:
                    fv_i.append(i); fv_d.append(1); fv_v.append(fT[k]); borrar = True
            else:
                if h[i] >= fB[k]:
                    fv_i.append(i); fv_d.append(-1); fv_v.append(fB[k]); borrar = True
            if borrar:
                fT[k] = fT[nf - 1]; fB[k] = fB[nf - 1]; fD[k] = fD[nf - 1]; fC[k] = fC[nf - 1]; nf -= 1
            else: k += 1
        # ---- pivotes internos ----
        if i >= size_int:
            p = i - size_int
            mx = h[p + 1]; mn = l[p + 1]
            for j in range(p + 1, i + 1):
                if h[j] > mx: mx = h[j]
                if l[j] < mn: mn = l[j]
            nl = -1
            if h[p] > mx: nl = 0
            elif l[p] < mn: nl = 1
            if nl != -1 and legI != -1 and nl != legI:
                if nl == 1: iL = l[p]; iLc = False; iLidx = p
                else: iH = h[p]; iHc = False; iHidx = p
            if nl != -1: legI = nl
        # ---- pivotes swing ----
        if i >= size_swing:
            p = i - size_swing
            mx = h[p + 1]; mn = l[p + 1]
            for j in range(p + 1, i + 1):
                if h[j] > mx: mx = h[j]
                if l[j] < mn: mn = l[j]
            nl = -1
            if h[p] > mx: nl = 0
            elif l[p] < mn: nl = 1
            if nl != -1 and legS != -1 and nl != legS:
                if nl == 1: sL = l[p]; sLc = False
                else: sH = h[p]; sHc = False
            if nl != -1: legS = nl
        # ---- rupturas internas -> OB ----
        if i > 0:
            if not iHc and c[i - 1] <= iH and c[i] > iH:
                iHc = True; rint[i] = 1; choch[i] = (trI == -1); trI = 1
                if iHidx < i - 1 and nob < 200:
                    q = iHidx
                    for j in range(iHidx, i):
                        if pl[j] < pl[q]: q = j
                    obT[nob] = max(ph[q], pl[q]); obB[nob] = min(ph[q], pl[q]); obD[nob] = 1; obC[nob] = i; nob += 1
            if not iLc and c[i - 1] >= iL and c[i] < iL:
                iLc = True; rint[i] = -1; choch[i] = (trI == 1); trI = -1
                if iLidx < i - 1 and nob < 200:
                    q = iLidx
                    for j in range(iLidx, i):
                        if ph[j] > ph[q]: q = j
                    obT[nob] = max(ph[q], pl[q]); obB[nob] = min(ph[q], pl[q]); obD[nob] = -1; obC[nob] = i; nob += 1
            if not sHc and c[i - 1] <= sH and c[i] > sH:
                sHc = True; rsw[i] = 1; trS = 1
            if not sLc and c[i - 1] >= sL and c[i] < sL:
                sLc = True; rsw[i] = -1; trS = -1
        tsw[i] = trS
        # ---- FVG (LuxAlgo, umbral automatico) ----
        if i >= 2:
            d = (c[i - 1] - o[i - 1]) / o[i - 1] * 100.0
            cum += abs(d)
            thr = cum / (i - 1) * 2.0
            if l[i] > h[i - 2] and c[i - 1] > h[i - 2] and d > thr and nf < 400:
                fT[nf] = l[i]; fB[nf] = h[i - 2]; fD[nf] = 1; fC[nf] = i; nf += 1
            elif h[i] < l[i - 2] and c[i - 1] < l[i - 2] and -d > thr and nf < 400:
                fT[nf] = l[i - 2]; fB[nf] = h[i]; fD[nf] = -1; fC[nf] = i; nf += 1
    return (rint, choch, rsw, tsw,
            np.array(ob_i, np.int64), np.array(ob_d, np.int64), np.array(ob_v, np.float64),
            np.array(fv_i, np.int64), np.array(fv_d, np.int64), np.array(fv_v, np.float64))


@njit(cache=True)
def simular2(T, O, H, L, S, t0, t1, d, nivel, sld, tpd, tsal, spct, unidades, limite):
    """Entrada: limite=True -> primer minuto en [t0,t1) que toca 'nivel'; False -> apertura del minuto t0.
    Sale por SL (si sld>0), TP (si tpd>0) o a la apertura del minuto tsal. Mismo minuto SL y TP -> SL."""
    m = len(t0); nT = len(T)
    je = np.full(m, -1, np.int64); js = np.full(m, -1, np.int64)
    PE = np.zeros(m); PS = np.zeros(m); SP = np.zeros(m)
    for r in range(m):
        q0 = np.searchsorted(T, t0[r]); q1 = np.searchsorted(T, t1[r])
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
        b = min(np.searchsorted(T, tsal[r]), nT - 1)
        if b <= j: b = j + 1
        sl = pe - d[r] * sld[r] if sld[r] > 0 else (-1e300 if d[r] == 1 else 1e300)
        tp = pe + d[r] * tpd[r] if tpd[r] > 0 else (1e300 if d[r] == 1 else -1e300)
        ps = O[b]; k = b
        for q in range(j, b):
            hs = (L[q] <= sl) if d[r] == 1 else (H[q] >= sl)
            ht = (H[q] >= tp) if d[r] == 1 else (L[q] <= tp)
            if hs:
                if q == j: ps = sl
                else: ps = min(sl, O[q]) if d[r] == 1 else max(sl, O[q])
                k = q; break
            if ht and q > j or (ht and q == j and not limite):
                ps = tp; k = q; break
            if ht and q == j and limite:
                # el mismo minuto de la entrada limite: solo cuenta si el precio sigue despues (conservador: siguiente minuto)
                pass
        je[r] = j; js[r] = k; PE[r] = pe; PS[r] = ps
        SP[r] = max(S[j], spct * pe) * unidades
    return je, js, PE, PS, SP

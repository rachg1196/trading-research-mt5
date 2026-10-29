# -*- coding: utf-8 -*-
"""Estrategia W y M: senales, confirmacion en M1, entrada, salida a N velas, costes y comparacion con el azar."""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from motor import MIN
import detector  # copia del proyecto W y M (mismos parametros)


def senales(tfdf):
    """Patrones W/M detectados en la TF. Devuelve tipo (+1 W compra, -1 M venta), tiempo de cierre de la vela senal,
    cuello y extremo (piso mas bajo de la W / techo mas alto de la M)."""
    r = detector.detectar(tfdf[["time", "open", "high", "low", "close"]])
    if len(r) == 0:
        return pd.DataFrame(columns=["tipo", "i_senal", "t_cierre", "cuello", "extremo"])
    pisos = r[["p_L1", "p_L2", "p_L3"]].to_numpy(float)
    ext = np.where(r.tipo == "W", np.nanmin(pisos, axis=1), np.nanmax(pisos, axis=1))
    return pd.DataFrame({"tipo": np.where(r.tipo == "W", 1, -1), "i_senal": r.i_senal.to_numpy(),
                         "t_cierre": 0, "cuello": r.cuello.to_numpy(float), "extremo": ext})


def confirmar(sen, tfdf, tf, m1, punto, expira_velas=10):
    """Confirmacion como el EA, con velas M1: despues del cierre de la vela senal, la primera vela M1 que
    (a) va a favor (W: cierra arriba de su apertura; M: abajo), (b) cierra mas alla del cuello y
    (c) no abre con salto (|apertura - cierre anterior| <= spread de esa vela).
    Se descarta si toca el extremo o si pasan 'expira_velas' velas de la TF sin confirmar.
    Entrada = apertura de la vela M1 siguiente."""
    per = MIN[tf] * 60
    t = m1.time.to_numpy(); o = m1.open.to_numpy(); h = m1.high.to_numpy(); l = m1.low.to_numpy()
    c = m1.close.to_numpy(); sp = m1.spread.to_numpy() * punto
    cprev = np.r_[np.nan, c[:-1]]
    t_cierre = tfdf.time.to_numpy()[sen.i_senal.to_numpy()] + per
    out = []
    for k in range(len(sen)):
        tipo = sen.tipo.iat[k]; cue = sen.cuello.iat[k]; ext = sen.extremo.iat[k]
        a = np.searchsorted(t, t_cierre[k]); b = np.searchsorted(t, t_cierre[k] + expira_velas * per)
        ent = -1
        for j in range(a, min(b, len(t) - 1)):
            if (tipo == 1 and l[j] < ext) or (tipo == -1 and h[j] > ext):
                break
            favor = c[j] > o[j] if tipo == 1 else c[j] < o[j]
            mas_alla = c[j] > cue if tipo == 1 else c[j] < cue
            sin_salto = abs(o[j] - cprev[j]) <= max(sp[j], 1e-12)
            if favor and mas_alla and sin_salto:
                ent = j + 1
                break
        out.append(ent)
    s = sen.copy(); s["t_cierre"] = t_cierre; s["j_ent"] = out
    return s[s.j_ent >= 0].reset_index(drop=True)




def simular(ent_idx, tipos, m1, tf, n_velas, costes, una_a_la_vez=True):
    """Simula entradas en indices M1 (apertura). Salida: apertura de la primera vela M1 con tiempo >= entrada + N velas TF.
    Resultado en USD para el LOTE MINIMO, ya con spread y swap."""
    per = MIN[tf] * 60
    t = m1.time.to_numpy(); o = m1.open.to_numpy()
    ent_idx = np.asarray(ent_idx); tipos = np.asarray(tipos)
    sal_idx = np.searchsorted(t, t[ent_idx] + n_velas * per)
    ok = sal_idx < len(t)
    ent_idx, tipos, sal_idx = ent_idx[ok], tipos[ok], sal_idx[ok]
    if una_a_la_vez and len(ent_idx):
        keep = []; libre = -1
        for k in range(len(ent_idx)):
            if ent_idx[k] >= libre:
                keep.append(k); libre = sal_idx[k]
        keep = np.array(keep, int)
        ent_idx, tipos, sal_idx = ent_idx[keep], tipos[keep], sal_idx[keep]
    pe, ps = o[ent_idx], o[sal_idx]
    bruto = (ps - pe) * tipos * costes["unidades"]          # unidades = contrato * lote minimo
    spread = costes_spread(m1, ent_idx, costes)
    swap = costes_swap(t[ent_idx], t[sal_idx], pe, tipos, costes)
    neto = bruto - spread + swap
    return pd.DataFrame({"j_ent": ent_idx, "j_sal": sal_idx, "tipo": tipos, "t_ent": t[ent_idx], "p_ent": pe,
                         "p_sal": ps, "bruto": bruto, "spread": spread, "swap": swap, "neto": neto})


def costes_spread(m1, idx, costes):
    """Spread pagado = el mayor entre el spread de la vela de entrada y el piso realista (% del precio medido)."""
    sp_vela = m1.spread.to_numpy()[idx] * costes["punto"]
    piso = costes["spread_pct"] * m1.open.to_numpy()[idx]
    return np.maximum(sp_vela, piso) * costes["unidades"]


def _cuenta(d0, d1, r):
    """Cuantos enteros d en (d0, d1] cumplen d % 7 == r."""
    return np.floor((d1 - r) / 7) - np.floor((d0 - r) / 7)


def costes_swap(t_ent, t_sal, precio, tipos, costes):
    """Swap por cada rollover (medianoche del servidor) cruzado. Solo se cobran las noches que empiezan de lunes a viernes;
    la del dia 'swap_triple' cuenta x3 (asi el fin de semana se cobra una sola vez, por adelantado)."""
    d0 = np.asarray(t_ent) // 86400; d1 = np.asarray(t_sal) // 86400
    noches = np.zeros(len(d0))
    for wd in range(1, 6):                       # noche que empieza lunes..viernes
        r = (wd - 3) % 7                         # medianoche del dia d => noche que empezo el dia d-1; (d-1+4)%7 == wd
        noches += _cuenta(d0, d1, r) * (3 if wd == costes["swap_triple"] else 1)
    lado = np.where(np.asarray(tipos) == 1, costes["swap_long"], costes["swap_short"])
    if costes["swap_modo"] == 5:   # % anual sobre el precio
        return noches * lado / 100 / 360 * precio * costes["unidades"]
    if costes["swap_modo"] == 1:   # en puntos
        return noches * lado * costes["punto"] * costes["unidades"]
    return noches * 0.0


def azar(m1, tf, n_velas, tipos, costes, K=2000, semilla=7, validos=None):
    """K conjuntos de entradas al azar (mismo numero y mismas direcciones), misma salida y mismos costes.
    Devuelve la media por operacion de cada conjunto."""
    rng = np.random.default_rng(semilla)
    per = MIN[tf] * 60
    t = m1.time.to_numpy(); o = m1.open.to_numpy()
    sal = np.searchsorted(t, t + n_velas * per)
    cand = np.nonzero(sal < len(t))[0] if validos is None else validos
    n = len(tipos)
    medias = np.empty(K)
    # precalculo vectorizado
    ret = (o[np.minimum(sal, len(t) - 1)] - o) * costes["unidades"]
    spr = np.maximum(m1.spread.to_numpy() * costes["punto"], costes["spread_pct"] * o) * costes["unidades"]
    for k in range(K):
        j = rng.choice(cand, n, replace=True)
        tp = rng.permutation(tipos)
        sw = costes_swap(t[j], t[sal[j]], o[j], tp, costes)
        medias[k] = np.mean(ret[j] * tp - spr[j] + sw)
    return medias

# -*- coding: utf-8 -*-
"""
Detector de patrones W (doble/triple piso) y M (doble/triple techo).

Idea (en palabras de Raul):
  - Venia una tendencia (para W: bajista). Se forma el piso 1 (minimo mas bajo).
  - Rebote -> maximo que define la linea del cuello.
  - Segundo piso: puede quedar MAS ALTO, IGUAL o un poco MAS BAJO (barrida) que el piso 1.
  - A veces 3 toques (triple piso).
  - Senal: cierre por encima del cuello. M = todo al reves.

Detalles tecnicos:
  - Puntos de giro por ZigZag con umbral = K_ATR * ATR(14): no depende de contar velas.
  - Todo es causal: un punto de giro solo se usa desde la vela en que queda confirmado.
  - Tolerancia de "zona" basada en ATR.
"""
import numpy as np
import pandas as pd

PARAMS = dict(
    atr_n=14,
    k_atr=1.5,          # tamano minimo de un tramo del zigzag (en ATR)
    tol_atr=0.5,        # tolerancia de zona "igual" (en ATR)
    max_barrida=0.5,    # el 2do piso puede perforar el 1ro hasta 50% del rebote
    min_caida=1.0,      # la caida previa al piso 1 debe ser >= rebote (contexto de tendencia)
    espera_factor=1.0,  # tiempo max para romper el cuello = factor * duracion del patron
    espera_min=5,
    min_velas=3,        # cada tramo del patron (rebote y retroceso) dura al menos 3 velas
    min_rebote_atr=2.5, # el rebote (piso 1 -> cuello) mide al menos 2.5 ATR
)


def atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    return a


def zigzag(h, l, a, k):
    """Devuelve lista de pivotes (tipo, idx, precio, idx_confirmacion). tipo +1=maximo, -1=minimo."""
    piv = []
    n = len(h)
    d = 0
    ext_i, ext_p = 0, h[0]
    lo_i, lo_p = 0, l[0]
    hi_i, hi_p = 0, h[0]
    for i in range(1, n):
        th = k * a[i]
        if d == 0:
            if h[i] > hi_p:
                hi_i, hi_p = i, h[i]
            if l[i] < lo_p:
                lo_i, lo_p = i, l[i]
            if hi_p - lo_p >= th:
                if hi_i > lo_i:
                    piv.append((-1, lo_i, lo_p, i)); d = 1; ext_i, ext_p = hi_i, hi_p
                else:
                    piv.append((1, hi_i, hi_p, i)); d = -1; ext_i, ext_p = lo_i, lo_p
            continue
        if d == 1:
            if h[i] > ext_p:
                ext_i, ext_p = i, h[i]
            elif ext_p - l[i] >= th:
                piv.append((1, ext_i, ext_p, i)); d = -1; ext_i, ext_p = i, l[i]
        else:
            if l[i] < ext_p:
                ext_i, ext_p = i, l[i]
            elif h[i] - ext_p >= th:
                piv.append((-1, ext_i, ext_p, i)); d = 1; ext_i, ext_p = i, h[i]
    return piv


def _buscar_w(h, l, c, a, piv, P):
    """Busca patrones alcistas (W) usando la lista de pivotes. Devuelve lista de dicts."""
    res = []
    lows = [j for j, p in enumerate(piv) if p[0] == -1]
    for jj in lows:
        # candidatos: doble (L1,H1,L2) y triple (L1,H1,L2,H2,L3)
        for toques in (2, 3):
            j1 = jj - 2 * (toques - 1)          # indice del piso 1 en piv
            if j1 - 2 < 0:
                continue
            seq = piv[j1 - 1: jj + 1]           # H0, L1, H1, L2, (H2, L3)
            H0 = seq[0]
            pisos = seq[1::2]
            techos = seq[2::2]
            L1 = pisos[0]
            L0 = piv[j1 - 2]
            # contexto: venia bajando (piso 1 es minimo mas bajo que el anterior)
            if not (L1[2] < L0[2]):
                continue
            cuello = max(t[2] for t in techos)
            rebote = cuello - L1[2]
            if rebote <= 0:
                continue
            if (H0[2] - L1[2]) < P["min_caida"] * rebote:
                continue
            if rebote < P["min_rebote_atr"] * a[L1[1]]:
                continue
            idxs = [p[1] for p in seq[1:]]
            if any(b - a_ < P["min_velas"] for a_, b in zip(idxs[:-1], idxs[1:])):
                continue
            tol = P["tol_atr"] * a[pisos[-1][1]]
            # los pisos siguientes no pueden perforar demasiado el piso 1
            limite = L1[2] - P["max_barrida"] * rebote
            if any(p[2] < limite for p in pisos[1:]):
                continue
            if toques == 3:
                # en triple, el 2do techo debe quedar en zona del 1ro o por debajo (no rompe el cuello)
                if techos[1][2] > techos[0][2] + tol:
                    continue
            Lu = pisos[-1]
            d = Lu[2] - L1[2]
            variante = "igual" if abs(d) <= tol else ("alto" if d > 0 else "barrida")
            # ruptura del cuello, desde que el ultimo piso queda confirmado
            inicio = Lu[3]
            dur = Lu[1] - L1[1] + 1
            fin = min(len(c) - 2, inicio + max(P["espera_min"], int(P["espera_factor"] * dur)))
            invalido = min(p[2] for p in pisos) - tol
            sig = None
            for i in range(inicio, fin + 1):
                if l[i] < invalido:
                    break
                if c[i] > cuello:
                    sig = i
                    break
            if sig is None:
                continue
            res.append(dict(
                toques=toques, variante=variante,
                i_H0=H0[1], p_H0=H0[2],
                i_L1=L1[1], p_L1=L1[2], i_H1=techos[0][1], p_H1=techos[0][2],
                i_L2=pisos[1][1], p_L2=pisos[1][2],
                i_H2=techos[1][1] if toques == 3 else -1, p_H2=techos[1][2] if toques == 3 else np.nan,
                i_L3=pisos[2][1] if toques == 3 else -1, p_L3=pisos[2][2] if toques == 3 else np.nan,
                cuello=cuello, i_conf=Lu[3], i_senal=sig,
                retroceso=(cuello - Lu[2]) / rebote,  # 1 = mismo nivel, <1 piso alto, >1 barrida
                atr=a[sig],
            ))
    if not res:
        return pd.DataFrame()
    df = pd.DataFrame(res)
    # una sola senal por vela de ruptura: nos quedamos con la de mas toques
    df = df.sort_values(["i_senal", "toques"]).drop_duplicates("i_senal", keep="last")
    return df


def detectar(df, P=None):
    """df con columnas time, open, high, low, close. Devuelve DataFrame de patrones W y M."""
    P = {**PARAMS, **(P or {})}
    h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    a = atr(h, l, c, P["atr_n"])
    out = []
    # W
    piv = zigzag(h, l, a, P["k_atr"])
    w = _buscar_w(h, l, c, a, piv, P)
    if len(w):
        w["tipo"] = "W"; out.append(w)
    # M = espejo de precios
    hm, lm, cm = -l, -h, -c
    pivm = zigzag(hm, lm, a, P["k_atr"])
    m = _buscar_w(hm, lm, cm, a, pivm, P)
    if len(m):
        for col in ["p_H0", "p_L1", "p_H1", "p_L2", "p_H2", "p_L3", "cuello"]:
            m[col] = -m[col]
        m["tipo"] = "M"; out.append(m)
    if not out:
        return pd.DataFrame()
    r = pd.concat(out, ignore_index=True).sort_values("i_senal").reset_index(drop=True)
    r["t_senal"] = df["time"].to_numpy()[r["i_senal"]]
    # entrada: apertura de la vela siguiente a la senal
    r["entrada"] = df["open"].to_numpy()[np.minimum(r["i_senal"] + 1, len(df) - 1)]
    return r

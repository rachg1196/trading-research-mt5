# -*- coding: utf-8 -*-
"""3 estrategias de scalping (texto de la otra IA). Senales en velas cerradas; ejecucion simulada en M1.
TP = (1 USD + spread en USD) en precio, con lote minimo. SL estructural +10 puntos. Filtro R:R >= 1.5 (TP/SL).
Si en la misma vela M1 se tocan SL y TP, cuenta como SL (conservador). Tiempo maximo: 1 dia (cierre a mercado)."""
import numpy as np, pandas as pd

MAX_MIN = 1440
RR_MIN = 1.5


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()


# ---------------- Estrategia 1: EMAs 9/21/50 + RSI (M5) ----------------
def e1(df, k_ret=20, swing=10):
    o, h, l, c = (df[x].to_numpy(float) for x in ["open", "high", "low", "close"])
    e9, e21, e50, r = ema(c, 9), ema(c, 21), ema(c, 50), rsi(c)
    out = []
    for d in (1, -1):
        cruce = -10**9
        for i in range(51, len(c)):
            if d == 1:
                alin = e9[i] > e21[i] > e50[i]
                if e9[i - 1] <= e21[i - 1] and e9[i] > e21[i] and e21[i] > e50[i]: cruce = i
            else:
                alin = e9[i] < e21[i] < e50[i]
                if e9[i - 1] >= e21[i - 1] and e9[i] < e21[i] and e21[i] < e50[i]: cruce = i
            if not alin or i - cruce > k_ret or i == cruce:
                continue
            if d == 1:
                toca = l[i] <= e9[i] and l[i] > e50[i]          # retroceso a EMA9/21 sin romper EMA50
                conf = c[i] > o[i] and r[i] > 50 and c[i] > e9[i]
            else:
                toca = h[i] >= e9[i] and h[i] < e50[i]
                conf = c[i] < o[i] and r[i] < 50 and c[i] < e9[i]
            if toca and conf:
                sl = (l[i - swing + 1:i + 1].min() if d == 1 else h[i - swing + 1:i + 1].max())
                out.append((i, d, sl)); cruce = -10**9          # una entrada por cruce
    return out


# ---------------- Estrategia 2: Donchian 20 M5 + EMA200 M15 ----------------
def e2(df, df15, k_pb=10):
    o, h, l, c = (df[x].to_numpy(float) for x in ["open", "high", "low", "close"])
    t = df.time.to_numpy()
    up = pd.Series(h).rolling(20).max().shift(1).to_numpy(); dn = pd.Series(l).rolling(20).min().shift(1).to_numpy()
    e200 = ema(df15.close.to_numpy(float), 200)
    t15c = df15.time.to_numpy() + 900                                   # cierre de cada vela M15
    k15 = np.searchsorted(t15c, t + 300, side="right") - 1              # ultima M15 cerrada al cierre de la vela M5
    trend = np.where(k15 >= 200, np.sign(df15.close.to_numpy(float)[np.maximum(k15, 0)] - e200[np.maximum(k15, 0)]), 0)
    out = []
    for d in (1, -1):
        rot = None
        for i in range(21, len(c)):
            if d == 1 and trend[i] == 1 and c[i] > up[i]:
                rot = (i, up[i], (up[i] + dn[i]) / 2); continue
            if d == -1 and trend[i] == -1 and c[i] < dn[i]:
                rot = (i, dn[i], (up[i] + dn[i]) / 2); continue
            if rot is None: continue
            ib, nivel, medio = rot
            if i - ib > k_pb or trend[i] != d:
                rot = None; continue
            if d == 1:
                if c[i] < medio: rot = None; continue
                if l[i] <= nivel and c[i] > nivel and c[i] > o[i]:
                    out.append((i, 1, l[ib:i + 1].min())); rot = None
            else:
                if c[i] > medio: rot = None; continue
                if h[i] >= nivel and c[i] < nivel and c[i] < o[i]:
                    out.append((i, -1, h[ib:i + 1].max())); rot = None
    return out


# ---------------- Estrategia 3: barrida del rango asiatico ----------------
def e3(df, tf_min):
    """Rango asiatico = 00:00-08:00 UTC. Operable 08:00-17:00 UTC. Una operacion por lado y dia."""
    o, h, l, c = (df[x].to_numpy(float) for x in ["open", "high", "low", "close"])
    utc = pd.to_datetime(df.time, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    hora = (utc.dt.hour + utc.dt.minute / 60).to_numpy(); dia = utc.dt.date.to_numpy()
    out = []; i = 0; n = len(c)
    rango = {}
    for k in range(n):
        if hora[k] + tf_min / 60 <= 8:
            a = rango.setdefault(dia[k], [-np.inf, np.inf, 0]); a[0] = max(a[0], h[k]); a[1] = min(a[1], l[k]); a[2] += 1
    usado = set(); ext = {}
    for k in range(1, n):
        if not (8 <= hora[k] < 17) or dia[k] not in rango: continue
        hi, lo, nb = rango[dia[k]]
        if nb < 4: continue
        key = dia[k]
        # venta: rompe falso el techo y cierra dentro
        if h[k] > hi:
            ext[(key, -1)] = max(ext.get((key, -1), -np.inf), h[k])
        if (key, -1) in ext and (key, -1) not in usado and c[k] < hi and c[k] > lo:
            cuerpo = abs(c[k] - o[k]); mecha = h[k] - max(o[k], c[k])
            pin = mecha >= 2 * cuerpo and c[k] <= o[k] + cuerpo
            env = c[k] < o[k] and c[k - 1] > o[k - 1] and o[k] >= c[k - 1] and c[k] <= o[k - 1]
            if h[k] > hi and (pin or env):
                out.append((k, -1, ext[(key, -1)], (hi + lo) / 2)); usado.add((key, -1))
        if l[k] < lo:
            ext[(key, 1)] = min(ext.get((key, 1), np.inf), l[k])
        if (key, 1) in ext and (key, 1) not in usado and c[k] > lo and c[k] < hi:
            cuerpo = abs(c[k] - o[k]); mecha = min(o[k], c[k]) - l[k]
            pin = mecha >= 2 * cuerpo
            env = c[k] > o[k] and c[k - 1] < o[k - 1] and o[k] <= c[k - 1] and c[k] >= o[k - 1]
            if l[k] < lo and (pin or env):
                out.append((k, 1, ext[(key, 1)], (hi + lo) / 2)); usado.add((key, 1))
    return out


# ---------------- Ejecucion en M1 ----------------
def ejecutar(t_ent, d, sl_lvl, tp_dist_fn, m1, punto, unidades, spread_pct, tp_medio=None):
    """t_ent: tiempo de entrada (apertura de la vela siguiente a la confirmacion).
    Devuelve dict con resultado o None si el filtro R:R lo descarta."""
    tm = m1["t"]; j = np.searchsorted(tm, t_ent)
    if j >= len(tm) - 2: return None
    pe = m1["o"][j]
    spr_price = max(m1["s"][j] * punto, spread_pct * pe)
    sl = sl_lvl - d * 10 * punto
    sl_dist = (pe - sl) * d
    if sl_dist <= 0: return None
    tp_dist = (1.0 + spr_price * unidades) / unidades            # 1 USD neto + spread
    if tp_medio is not None:
        dm = (tp_medio - pe) * d
        if 0 < dm < tp_dist: tp_dist = dm                        # la linea media si esta mas cerca
    if tp_dist / sl_dist < RR_MIN: return None
    tp = pe + d * tp_dist
    b = min(np.searchsorted(tm, tm[j] + MAX_MIN * 60), len(tm) - 1)
    hh = m1["h"][j:b]; ll = m1["l"][j:b]
    if d == 1: hit_sl = ll <= sl; hit_tp = hh >= tp
    else: hit_sl = hh >= sl; hit_tp = ll <= tp
    ks = np.argmax(hit_sl) if hit_sl.any() else 10**9
    kt = np.argmax(hit_tp) if hit_tp.any() else 10**9
    if ks == 10**9 and kt == 10**9:
        ps = m1["o"][b]; motivo = "tiempo"; ksal = b
    elif ks <= kt:
        ps = min(sl, m1["o"][j + ks]) if d == 1 else max(sl, m1["o"][j + ks]); motivo = "sl"; ksal = j + ks
        if ks == 0: ps = sl
    else:
        ps = tp; motivo = "tp"; ksal = j + kt
    bruto = (ps - pe) * d * unidades
    return dict(j=j, d=d, pe=pe, ps=ps, bruto=bruto, spread=spr_price * unidades, neto=bruto - spr_price * unidades,
                motivo=motivo, minutos=(tm[ksal] - tm[j]) / 60, sl_dist=sl_dist, tp_dist=tp_dist)

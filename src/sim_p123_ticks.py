# -*- coding: utf-8 -*-
"""Patron 123 EA (config de Raul) simulado con ticks reales: M1,M2,M3,M5,M6 | pierna H1 | toques 3-4 con vela de
rechazo | SL = TP = floor(ATR14 x 1) | lote 0,10 | 1 por TF y mercado. Salida por SL/TP con bid/ask reales."""
import sys, numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, "src")
from lineas_nb import pivotes, toques_bajistas, pierna
from smc_nb import atr_sma
UN = 0.1; MULT = 1.0
TFS = {"M1": 1, "M2": 2, "M3": 3, "M5": 5, "M6": 6}

def atr_prev(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    a = pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).ewm(alpha=1/14, adjust=False).mean().to_numpy()
    return np.r_[a[0], a[:-1]]

@njit(cache=True)
def sim(ts, bid, ask, t_ent, d, dist):
    n = len(t_ent); res = np.zeros((n, 4)); k0 = 0
    orden = np.argsort(t_ent)
    for rr in range(n):
        r = orden[rr]
        k0 = np.searchsorted(ts, t_ent[r])
        if k0 >= len(ts) - 1: res[r, 0] = -1; continue
        pe = ask[k0] if d[r] == 1 else bid[k0]
        sl = pe - d[r] * dist[r]; tp = pe + d[r] * dist[r]
        k = k0; hecho = False
        while k < len(ts):
            px = bid[k] if d[r] == 1 else ask[k]
            if (d[r] == 1 and (px <= sl or px >= tp)) or (d[r] == -1 and (px >= sl or px <= tp)):
                res[r, 0] = 1; res[r, 1] = (px - pe) * d[r]; res[r, 2] = ts[k]; res[r, 3] = 1 if (px - pe) * d[r] < 0 else 2
                hecho = True; break
            k += 1
        if not hecho: res[r, 0] = -1
    return res

ops = []
for SIM in ["BreakX600", "TrendX600", "SwitchX600"]:
    tk = pd.read_csv(f"datos/ticks/{SIM}_ticks.csv.gz")
    tk = tk[(tk.bid > 0) & (tk.ask > 0)].sort_values("time_msc").reset_index(drop=True)
    ts = (tk.time_msc // 1000).to_numpy(np.int64); bid = tk.bid.to_numpy(float); ask = tk.ask.to_numpy(float)
    ser = pd.Series(bid, index=pd.to_datetime(tk.time_msc, unit="ms"))
    # pierna H1
    hb = ser.resample("60min").ohlc().dropna()
    hh, hl, hc = hb.high.to_numpy(), hb.low.to_numpy(), hb.close.to_numpy()
    ph, pl = pivotes(hh, hl); est = pierna(hh, hl, hc, ph, pl)
    hcierre = hb.index.values.astype("datetime64[s]").astype(np.int64) + 3600
    for tf, mins in TFS.items():
        b = ser.resample(f"{mins}min").ohlc().dropna()
        o, h, l, c = (b[x].to_numpy(float) for x in ["open", "high", "low", "close"])
        bt = b.index.values.astype("datetime64[s]").astype(np.int64); per = mins * 60
        ap = atr_prev(h, l, c); a14 = atr_sma(h, l, c, 14)
        for d in (-1, 1):
            if d == -1:
                ph2, pl2 = pivotes(h, l); bi, bn, bv = toques_bajistas(h, l, c, ap, ph2, pl2)
                L = bv + 0.1 * ap[bi]
                cuerpo = abs(c[bi] - o[bi]); mecha = h[bi] - np.maximum(o[bi], c[bi])
                rech = (c[bi] < L) & ((c[bi] < o[bi]) | (mecha >= cuerpo))
            else:
                ph2, pl2 = pivotes(-l, -h); bi, bn, bv = toques_bajistas(-l, -h, -c, ap, ph2, pl2)
                L = -(bv + 0.1 * ap[bi])
                cuerpo = abs(c[bi] - o[bi]); mecha = np.minimum(o[bi], c[bi]) - l[bi]
                rech = (c[bi] > L) & ((c[bi] > o[bi]) | (mecha >= cuerpo))
            k = np.searchsorted(hcierre, bt[bi] + per, side="right") - 1
            pk = np.where(k >= 0, est[np.maximum(k, 0)], 0)
            sel = (bn >= 3) & (bn <= 4) & rech & (pk == d)
            bi = bi[sel]
            if len(bi) == 0: continue
            dist = a14[bi] * MULT
            dist = np.where(np.floor(dist) >= 1, np.floor(dist), dist)
            t_ent = bt[bi] + per
            r = sim(ts, bid, ask, t_ent, np.full(len(bi), d, np.int64), dist)
            for j in range(len(bi)):
                if r[j, 0] > 0:
                    ops.append((SIM, tf, d, t_ent[j], r[j, 2], r[j, 1] * UN, dist[j]))
ops = pd.DataFrame(ops, columns=["mercado", "tf", "dir", "t_ent", "t_sal", "usd", "dist"]).sort_values("t_ent").reset_index(drop=True)
# 1 operacion a la vez por mercado y TF (en cualquier direccion, como el EA)
keep = []; libre = {}
for i, r in ops.iterrows():
    key = (r.mercado, r.tf)
    if r.t_ent >= libre.get(key, 0): keep.append(i); libre[key] = r.t_sal
ops = ops.loc[keep].reset_index(drop=True)
ops["dia"] = pd.to_datetime(ops.t_ent, unit="s").dt.date
ops.to_csv("resultados/sinteticos/p123_ticks_ops.csv", index=False)
print("Operaciones en 30 dias:", len(ops), "| aciertos", round(100 * (ops.usd > 0).mean(), 1), "% | USD/op", round(ops.usd.mean(), 4),
      "| total", round(ops.usd.sum(), 2))
print(ops.groupby("mercado").usd.agg(["count", "mean", "sum"]).round(3))
print(ops.groupby("tf").usd.agg(["count", "mean", "sum"]).round(3))
print("ganancia media", round(ops.usd[ops.usd > 0].mean(), 3), "| perdida media", round(ops.usd[ops.usd < 0].mean(), 3))

def objetivo(meta):
    filas = []
    for dia, g in ops.groupby("dia"):
        g = g.sort_values("t_ent"); tomadas = []
        for _, r in g.iterrows():
            real = sum(x.usd for x in tomadas if x.t_sal <= r.t_ent)
            if meta and real >= meta: break
            tomadas.append(r)
        pnl = sum(x.usd for x in tomadas)
        filas.append((dia, len(tomadas), pnl))
    return pd.DataFrame(filas, columns=["dia", "ops", "usd"])

print("\nObjetivo diario | dias con ganancia | dia medio | peor dia | mejor dia | total 30 dias | saldo minimo empezando con 30")
for meta in [10, 15, 20, 30, None]:
    t = objetivo(meta); saldo = 30 + t.usd.cumsum()
    print(f"{('$'+str(meta)) if meta else 'todo el dia':>12} | {int((t.usd>0).sum())}/{len(t)} | {t.usd.mean():+7.2f} | {t.usd.min():+7.2f} | "
          f"{t.usd.max():+7.2f} | {t.usd.sum():+8.2f} | {saldo.min():7.2f}")

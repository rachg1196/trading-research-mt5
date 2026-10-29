# -*- coding: utf-8 -*-
"""Control: ?la ventaja es de la W/M o de cualquier ruptura (inercia del mercado)?"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector
MAX_VELAS = 100
SPREAD = 1.30


def simular(o, h, l, c, entradas, dirs, dist):
    """Barreras simetricas (version simple, SL llenado en su nivel). Ver fase3_realista.py."""
    n = len(c)
    out = np.empty(len(entradas))
    for t, (e, d, x) in enumerate(zip(entradas, dirs, dist)):
        fin = min(n, e + MAX_VELAS)
        E = o[e]
        hh = h[e:fin]; ll = l[e:fin]
        tp = (hh >= E + x) if d == 1 else (ll <= E - x)
        sl = (ll <= E - x) if d == 1 else (hh >= E + x)
        itp = np.argmax(tp) if tp.any() else 10**9
        isl = np.argmax(sl) if sl.any() else 10**9
        out[t] = -x if (isl <= itp and isl < 10**9) else (x if itp < 10**9 else d * (c[fin - 1] - E))
    return out - SPREAD
DATOS = sys.argv[1]
INICIO_VIVO = pd.Timestamp("2025-06-16")
N_RUPT = 10
rows = []
for s in ["BreakX_600", "TrendX_600", "SwitchX_600"]:
    for tf in ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M15"]:
        df = pd.read_parquet(os.path.join(DATOS, s, f"{tf}.parquet"))
        df = df[df["time"] >= INICIO_VIVO].reset_index(drop=True)
        o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        a = detector.atr(h, l, c, 14)
        n = len(df)
        pat = detector.detectar(df); pat = pat[pat.i_senal + 1 < n - MAX_VELAS]
        i = pat.i_senal.to_numpy(); d = np.where(pat.tipo == "W", 1, -1)
        Rp = simular(o, h, l, c, i + 1, d, 2 * a[i]) / (2 * a[i])
        # ruptura simple: cierre rompe el maximo/minimo de las ultimas N velas (primera ruptura)
        hh = pd.Series(h).shift(1).rolling(N_RUPT).max().to_numpy()
        ll = pd.Series(l).shift(1).rolling(N_RUPT).min().to_numpy()
        up = c > hh; dn = c < ll
        up_f = up & ~np.r_[False, up[:-1]]; dn_f = dn & ~np.r_[False, dn[:-1]]
        idx = np.where(up_f | dn_f)[0]; idx = idx[(idx > 50) & (idx < n - MAX_VELAS - 2)]
        dr = np.where(up_f[idx], 1, -1)
        Rb = simular(o, h, l, c, idx + 1, dr, 2 * a[idx]) / (2 * a[idx])
        # inercia: direccion de la ultima vela, en momentos al azar
        rng = np.random.default_rng(3)
        j = rng.integers(50, n - MAX_VELAS - 2, 20000)
        dj = np.where(c[j] >= o[j], 1, -1)
        Ri = simular(o, h, l, c, j + 1, dj, 2 * a[j]) / (2 * a[j])
        def z(x, y): return (x.mean() - y.mean()) / np.sqrt(x.var(ddof=1)/len(x) + y.var(ddof=1)/len(y))
        rows.append(dict(simbolo=s, tf=tf, n_WM=len(Rp), R_WM=Rp.mean(), acierto_WM=(Rp > 0).mean(),
                         n_ruptura=len(Rb), R_ruptura=Rb.mean(), acierto_ruptura=(Rb > 0).mean(),
                         R_inercia=Ri.mean(), acierto_inercia=(Ri > 0).mean(),
                         z_WM_vs_ruptura=z(Rp, Rb)))
r = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(r.round(3).to_string(index=False))
r.to_csv(sys.argv[2], index=False)

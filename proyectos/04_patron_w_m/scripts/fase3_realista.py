# -*- coding: utf-8 -*-
"""
FASE 3 (version realista) - Simulacion vela a vela sobre M1 con llenados realistas en saltos.

Por que: en estos indices el precio avanza en linea recta (~3 por minuto) y cada ~10 min hay un
SALTO (~30) que atraviesa los stops. Un SL "en su nivel exacto" es irreal cuando lo cruza un salto.

Reglas de llenado (conservadoras):
  - Entrada: apertura M1 del minuto siguiente a la senal; spread 130 pts (1.30) por operacion.
  - SL tocado en una vela M1 normal -> se llena en el SL.
  - SL tocado en una vela M1 con salto (rango > 4x mediana) -> se llena en el extremo de esa vela.
  - TP -> se llena en el TP (sin mejora). Si TP y SL en la misma vela M1 -> SL.
  - Maximo 100 velas de la temporalidad de la senal; si no toca nada, se cierra a mercado.
Se compara: W/M  vs  ruptura simple (10 velas)  vs  seguir la ultima vela  vs  azar.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector

DATOS, SALIDA = sys.argv[1], sys.argv[2]
INICIO_VIVO = pd.Timestamp("2025-06-16")
SPREAD = 1.30
KS = [1, 2, 3]
MAX_VELAS = 100
N_CTRL = 4000
MIN_TF = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M6": 6, "M10": 10, "M12": 12,
          "M15": 15, "M20": 20, "M30": 30, "H1": 60}
SIMBOLOS = ["BreakX_600", "TrendX_600", "SwitchX_600"]
os.makedirs(os.path.join(SALIDA, "resultados"), exist_ok=True)


def preparar_m1(s):
    m = pd.read_parquet(os.path.join(DATOS, s, "M1.parquet"))
    m = m[m["time"] >= INICIO_VIVO].reset_index(drop=True)
    rango = (m["high"] - m["low"]).to_numpy()
    salto = rango > 4 * np.median(rango)
    return m, salto


def simular_m1(m1, salto, idx_m1, dirs, dist, horizonte):
    o, h, l, c = (m1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(o)
    pnl = np.empty(len(idx_m1))
    for t, (e, d, x, H) in enumerate(zip(idx_m1, dirs, dist, horizonte)):
        fin = min(n, e + H)
        E = o[e]
        hh, ll, sj = h[e:fin], l[e:fin], salto[e:fin]
        if d == 1:
            tp = hh >= E + x; sl = ll <= E - x
        else:
            tp = ll <= E - x; sl = hh >= E + x
        itp = int(np.argmax(tp)) if tp.any() else 10**9
        isl = int(np.argmax(sl)) if sl.any() else 10**9
        if isl < 10**9 and isl <= itp:
            if sj[isl]:
                pnl[t] = (ll[isl] - E) if d == 1 else (E - hh[isl])
            else:
                pnl[t] = -x
        elif itp < 10**9:
            pnl[t] = x
        else:
            pnl[t] = d * (c[fin - 1] - E)
    return pnl - SPREAD


filas = []
rng = np.random.default_rng(11)
for s in SIMBOLOS:
    m1, salto = preparar_m1(s)
    t_m1 = m1["time"].to_numpy()
    for tf, mins in MIN_TF.items():
        df = pd.read_parquet(os.path.join(DATOS, s, f"{tf}.parquet"))
        df = df[df["time"] >= INICIO_VIVO].reset_index(drop=True)
        o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        a = detector.atr(h, l, c, 14)
        n = len(df)
        H = MAX_VELAS * mins
        lim = n - MAX_VELAS - 2

        def a_m1(i_tf):
            # minuto en que abre la vela siguiente a la senal
            t_ent = df["time"].to_numpy()[i_tf] + np.timedelta64(mins, "m")
            return np.searchsorted(t_m1, t_ent)

        grupos = {}
        pat = detector.detectar(df); pat = pat[(pat.i_senal > 50) & (pat.i_senal < lim)]
        grupos["W/M"] = (pat.i_senal.to_numpy(), np.where(pat.tipo == "W", 1, -1))
        hh = pd.Series(h).shift(1).rolling(10).max().to_numpy()
        lw = pd.Series(l).shift(1).rolling(10).min().to_numpy()
        up = c > hh; dn = c < lw
        upf = up & ~np.r_[False, up[:-1]]; dnf = dn & ~np.r_[False, dn[:-1]]
        ib = np.where(upf | dnf)[0]; ib = ib[(ib > 50) & (ib < lim)]
        if len(ib) > N_CTRL:
            ib = np.sort(rng.choice(ib, N_CTRL, replace=False))
        grupos["ruptura"] = (ib, np.where(upf[ib], 1, -1))
        ii = rng.integers(51, lim, N_CTRL)
        grupos["inercia"] = (ii, np.where(c[ii] >= o[ii], 1, -1))
        ir = rng.integers(51, lim, N_CTRL)
        grupos["azar"] = (ir, rng.choice([1, -1], N_CTRL))

        for g, (i_tf, d) in grupos.items():
            if len(i_tf) < 30:
                continue
            im = a_m1(i_tf)
            ok = im < len(m1) - 1
            i_tf, d, im = i_tf[ok], d[ok], im[ok]
            for k in KS:
                dist = k * a[i_tf]
                p = simular_m1(m1, salto, im, d, dist, np.full(len(im), H))
                R = p / dist
                filas.append(dict(simbolo=s.replace("_", " "), tf=tf, grupo=g, k=k, n=len(p),
                                  acierto=(p > 0).mean(), R_medio=R.mean(),
                                  R_se=R.std(ddof=1) / np.sqrt(len(R)),
                                  pts_medio=p.mean() / 0.01,
                                  dias=(df["time"].iloc[-1] - df["time"].iloc[0]).days))
        f = [x for x in filas if x["simbolo"] == s.replace("_", " ") and x["tf"] == tf and x["k"] == 2]
        print(s, tf, " | ".join(f"{x['grupo']}: R {x['R_medio']:+.3f} ({x['acierto']:.0%})" for x in f), flush=True)

res = pd.DataFrame(filas)
res.to_csv(os.path.join(SALIDA, "resultados", "fase3_realista.csv"), index=False)
print("listo")

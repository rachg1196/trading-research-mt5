# -*- coding: utf-8 -*-
"""
FASE 3 - Prueba rapida: ?el patron basico tiene ventaja sobre el azar despues de costes?

Para cada patron (datos de desarrollo desde 16-jun-2025):
  - Entrada: apertura de la vela siguiente a la senal. W = compra, M = venta.
  - Coste: spread fijo de 130 puntos (1.30 en precio) por operacion (el actual, conservador).
  - Salida por barreras simetricas TP = SL = k * ATR (k = 1, 2, 3); max 100 velas.
    Si en una misma vela se tocan TP y SL, se asume SL (conservador).
  - Tambien: recorrido maximo a favor (MFE) y en contra (MAE) en las 20 velas siguientes.
Comparacion: entradas AL AZAR en el mismo mercado/temporalidad/periodo, con la misma
proporcion de compras/ventas y las mismas reglas de salida (10 por cada patron).
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector

DATOS, SALIDA = sys.argv[1], sys.argv[2]
INICIO_VIVO = pd.Timestamp("2025-06-16")
SPREAD = 1.30           # precio (130 puntos)
PUNTO = 0.01
KS = [1, 2, 3]
MAX_VELAS = 100
H_MFE = 20
N_AZAR = 10
SIMBOLOS = ["BreakX_600", "TrendX_600", "SwitchX_600"]
TFS = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30", "H1"]
rng = np.random.default_rng(7)
os.makedirs(os.path.join(SALIDA, "resultados"), exist_ok=True)


def simular(o, h, l, c, entradas, dirs, dist):
    """Devuelve pnl en precio (neto de spread) para barreras simetricas de distancia 'dist'."""
    n = len(c)
    out = np.empty(len(entradas))
    for t, (e, d, x) in enumerate(zip(entradas, dirs, dist)):
        fin = min(n, e + MAX_VELAS)
        E = o[e]
        hh = h[e:fin]; ll = l[e:fin]
        if d == 1:
            tp = hh >= E + x; sl = ll <= E - x
        else:
            tp = ll <= E - x; sl = hh >= E + x
        itp = np.argmax(tp) if tp.any() else 10**9
        isl = np.argmax(sl) if sl.any() else 10**9
        if isl <= itp and isl < 10**9:
            out[t] = -x
        elif itp < 10**9:
            out[t] = x
        else:
            out[t] = d * (c[fin - 1] - E)
    return out - SPREAD


def mfe_mae(o, h, l, entradas, dirs):
    n = len(o)
    mfe = np.empty(len(entradas)); mae = np.empty(len(entradas))
    for t, (e, d) in enumerate(zip(entradas, dirs)):
        fin = min(n, e + H_MFE)
        E = o[e]
        if d == 1:
            mfe[t] = h[e:fin].max() - E; mae[t] = E - l[e:fin].min()
        else:
            mfe[t] = E - l[e:fin].min(); mae[t] = h[e:fin].max() - E
    return mfe, mae


filas, detalle = [], []
for s in SIMBOLOS:
    for tf in TFS:
        df = pd.read_parquet(os.path.join(DATOS, s, f"{tf}.parquet"))
        df = df[df["time"] >= INICIO_VIVO].reset_index(drop=True)
        o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        a = detector.atr(h, l, c, 14)
        pat = detector.detectar(df)
        pat = pat[pat["i_senal"] + 1 < len(df) - MAX_VELAS].reset_index(drop=True)
        if len(pat) < 30:
            continue
        ent = (pat["i_senal"] + 1).to_numpy()
        dirs = np.where(pat["tipo"] == "W", 1, -1)
        atr_s = a[pat["i_senal"].to_numpy()]     # ATR conocido al cierre de la vela de senal
        # azar: mismas proporciones de direccion, ATR del momento
        m = len(pat) * N_AZAR
        ent_r = rng.integers(50, len(df) - MAX_VELAS - 1, m)
        dirs_r = rng.choice(dirs, m)
        atr_r = a[ent_r - 1]
        mfe, mae = mfe_mae(o, h, l, ent, dirs)
        mfe_r, mae_r = mfe_mae(o, h, l, ent_r, dirs_r)
        fila = dict(simbolo=s.replace("_", " "), tf=tf, n=len(pat),
                    dias=(df["time"].iloc[-1] - df["time"].iloc[0]).days,
                    atr_pts=float(np.median(atr_s) / PUNTO),
                    spread_en_atr=float(SPREAD / np.median(atr_s)),
                    mfe20_med_pts=float(np.median(mfe) / PUNTO), mae20_med_pts=float(np.median(mae) / PUNTO),
                    mfe20_med_pts_azar=float(np.median(mfe_r) / PUNTO), mae20_med_pts_azar=float(np.median(mae_r) / PUNTO))
        for k in KS:
            p = simular(o, h, l, c, ent, dirs, k * atr_s)
            pr = simular(o, h, l, c, ent_r, dirs_r, k * atr_r)
            # en unidades de riesgo (R): pnl / (k*ATR)
            R = p / (k * atr_s); Rr = pr / (k * atr_r)
            dif = R.mean() - Rr.mean()
            se = np.sqrt(R.var(ddof=1) / len(R) + Rr.var(ddof=1) / len(Rr))
            fila.update({
                f"k{k}_acierto": float((p > 0).mean()), f"k{k}_acierto_azar": float((pr > 0).mean()),
                f"k{k}_R_medio": float(R.mean()), f"k{k}_R_medio_azar": float(Rr.mean()),
                f"k{k}_dif_R": float(dif), f"k{k}_z": float(dif / se),
                f"k{k}_pts_medio": float(p.mean() / PUNTO),
            })
            if k == 2:
                d_ = pat[["tipo", "variante", "toques", "t_senal"]].copy()
                d_["simbolo"] = s; d_["tf"] = tf; d_["R"] = R; d_["pts"] = p / PUNTO
                d_["mfe20_pts"] = mfe / PUNTO; d_["mae20_pts"] = mae / PUNTO
                detalle.append(d_)
        filas.append(fila)
        print(f"{s:<12}{tf:<4} n={len(pat):>5}  k2: acierto {fila['k2_acierto']:.1%} vs azar {fila['k2_acierto_azar']:.1%}"
              f" | R {fila['k2_R_medio']:+.3f} vs {fila['k2_R_medio_azar']:+.3f}  z={fila['k2_z']:+.2f}", flush=True)

res = pd.DataFrame(filas)
res.to_csv(os.path.join(SALIDA, "resultados", "fase3_resumen.csv"), index=False)
pd.concat(detalle).to_csv(os.path.join(SALIDA, "resultados", "fase3_operaciones_k2.csv"), index=False)
print("listo")

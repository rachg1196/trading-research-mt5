# -*- coding: utf-8 -*-
"""Prueba de filtro de tendencia con EMA sobre las senales W/M (datos de desarrollo).
Entrada: apertura de la vela siguiente a la senal. Salida: apertura N velas despues. Spread 130 pts.
Filtros (EMA calculada en la misma temporalidad, al cierre de la vela de senal):
  A favor   : W solo si cierre > EMA ; M solo si cierre < EMA   (patron a favor de la tendencia mayor)
  En contra : W solo si cierre < EMA ; M solo si cierre > EMA   (patron como giro real de tendencia)
  Pendiente : W solo si la EMA sube ; M solo si la EMA baja"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector
D = sys.argv[1]; INI = pd.Timestamp("2025-06-16"); SP = 1.30
rows = []
for s in ["BreakX_600", "TrendX_600", "SwitchX_600"]:
    for tf in ["M1","M2","M3","M4","M5","M6","M10","M15","M20","M30","H1"]:
        df = pd.read_parquet(f"{D}/{s}/{tf}.parquet")
        c_all = df.close
        emas = {L: c_all.ewm(span=L, adjust=False).mean().to_numpy() for L in (100, 200)}
        keep = (df.time >= INI).to_numpy(); off = np.argmax(keep)
        df2 = df[keep].reset_index(drop=True)
        o = df2.open.to_numpy(); c = df2.close.to_numpy(); n = len(o)
        dias = (df2.time.iloc[-1] - df2.time.iloc[0]).days
        p = detector.detectar(df2)
        i = p.i_senal.to_numpy(); d = np.where(p.tipo == "W", 1, -1)
        for N in [2, 5, 10]:
            ok = i + 1 + N < n
            ii, dd = i[ok], d[ok]
            pnl = dd * (o[ii + 1 + N] - o[ii + 1]) - SP
            base = dict(simbolo=s, tf=tf, N=N, dias=dias)
            rows.append({**base, "filtro": "sin filtro", "n": len(pnl), "pts": pnl.mean() / 0.01, "sd": pnl.std() / 0.01})
            for L, e in emas.items():
                ev = e[off + ii]; ev_prev = e[off + ii - 5]
                fav = np.where(dd == 1, c[ii] > ev, c[ii] < ev)
                pend = np.where(dd == 1, ev > ev_prev, ev < ev_prev)
                for nom, m in [(f"EMA{L} a favor", fav), (f"EMA{L} en contra", ~fav), (f"EMA{L} pendiente a favor", pend)]:
                    x = pnl[m]
                    rows.append({**base, "filtro": nom, "n": len(x), "pts": x.mean() / 0.01 if len(x) else np.nan,
                                 "sd": x.std() / 0.01 if len(x) > 1 else np.nan})
r = pd.DataFrame(rows)
r["se"] = r.sd / np.sqrt(r.n); r["z"] = r.pts / r.se
r["usd_dia"] = r.pts / 1000 * r.n / r.dias
r.to_csv(sys.argv[2], index=False)
pd.set_option("display.width", 220)
for N in [2, 5, 10]:
    x = r[r.N == N]
    g = x.groupby("filtro").apply(lambda q: pd.Series(dict(
        operaciones=q.n.sum(), pts_por_op=np.average(q.pts, weights=q.n), usd_dia_total=q.usd_dia.sum(),
        celdas_pos=int((q.pts > 0).sum()), celdas_z2=int((q.z > 2).sum()), celdas=len(q))))
    print(f"\n=== N = {N} velas ==="); print(g.round(2).to_string())

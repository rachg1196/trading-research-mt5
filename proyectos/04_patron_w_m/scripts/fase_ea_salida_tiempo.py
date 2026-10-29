# -*- coding: utf-8 -*-
"""Que habria pasado con salida por TIEMPO (cerrar despues de N velas), sin SL/TP.
Entrada: apertura de la vela siguiente a la senal. Salida: apertura N velas despues. Spread 130 pts."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector
D = sys.argv[1]; INI = pd.Timestamp("2025-06-16"); SP = 1.30
rows = []
for s in ["BreakX_600", "TrendX_600", "SwitchX_600"]:
    for tf in ["M1","M2","M3","M4","M5","M6","M10","M15","M20","M30","H1"]:
        df = pd.read_parquet(f"{D}/{s}/{tf}.parquet"); df = df[df.time >= INI].reset_index(drop=True)
        o = df.open.to_numpy(); n = len(o); dias = (df.time.iloc[-1]-df.time.iloc[0]).days
        p = detector.detectar(df); e = (p.i_senal + 1).to_numpy(); d = np.where(p.tipo == "W", 1, -1)
        for N in [1, 2, 3, 5, 10, 15, 20]:
            ok = e + N < n
            pnl = d[ok] * (o[e[ok] + N] - o[e[ok]]) - SP
            # control: mismas entradas con direccion al azar
            rng = np.random.default_rng(N)
            dr = rng.choice([1, -1], ok.sum())
            pr = dr * (o[e[ok] + N] - o[e[ok]]) - SP
            rows.append(dict(simbolo=s, tf=tf, N=N, n=ok.sum(), por_dia=ok.sum()/dias,
                             pts_medio=pnl.mean()/0.01, se_pts=pnl.std(ddof=1)/np.sqrt(ok.sum())/0.01,
                             acierto=(pnl > 0).mean(), pts_azar=pr.mean()/0.01,
                             usd_dia_lote01=pnl.mean()/0.01/1000*ok.sum()/dias))
r = pd.DataFrame(rows); r["z"] = r.pts_medio / r.se_pts
r.to_csv(sys.argv[2], index=False)
pd.set_option("display.width", 220)
print(r.pivot_table(index="tf", columns=["simbolo"], values="pts_medio", aggfunc="mean").round(0).reindex(["M1","M2","M3","M4","M5","M6","M10","M15","M20","M30","H1"]))
for N in [1,2,5,10,20]:
    x = r[r.N == N]
    print(f"N={N:>2}: media pts por operacion (todas las celdas) {np.average(x.pts_medio, weights=x.n):+.0f} | celdas z>2: {(x.z>2).sum()}/{len(x)} | z<-2: {(x.z<-2).sum()} | acierto medio {np.average(x.acierto, weights=x.n):.1%} | $/dia todas las celdas juntas (lote 0.10): {x.usd_dia_lote01.sum():+.2f}")

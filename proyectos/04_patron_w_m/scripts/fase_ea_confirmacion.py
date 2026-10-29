# -*- coding: utf-8 -*-
"""Compara: entrar directo vs entrar con confirmacion de continuidad (reglas aprobadas por Raul).
Confirmacion aproximada con velas M1 (los datos no tienen segundos): ultima vela M1 cerrada
a favor (bajista para M / alcista para W), sin salto, y cierre mas alla del cuello.
Descarte: 10 velas de la temporalidad sin entrar, o precio supera el techo (M) / piso (W) extremo.
Salida: N velas de la temporalidad desde la entrada. Spread 130 pts."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector
D = sys.argv[1]; INI = pd.Timestamp("2025-06-16"); SP = 1.30; EXP = 10
MIN = {"M1":1,"M2":2,"M3":3,"M4":4,"M5":5,"M6":6,"M10":10,"M15":15,"M20":20,"M30":30,"H1":60}
rows = []
for s in ["BreakX_600", "TrendX_600", "SwitchX_600"]:
    m1 = pd.read_parquet(f"{D}/{s}/M1.parquet"); m1 = m1[m1.time >= INI].reset_index(drop=True)
    t1 = m1.time.to_numpy(); o1, h1, l1, c1 = (m1[k].to_numpy() for k in ["open","high","low","close"])
    rg = h1 - l1; salto = rg > 4 * np.median(rg); n1 = len(m1)
    for tf, mins in MIN.items():
        df = pd.read_parquet(f"{D}/{s}/{tf}.parquet"); df = df[df.time >= INI].reset_index(drop=True)
        dias = (df.time.iloc[-1] - df.time.iloc[0]).days
        p = detector.detectar(df)
        tsig = df.time.to_numpy()[p.i_senal.to_numpy()] + np.timedelta64(mins, "m")   # cierre vela senal
        k0 = np.searchsorted(t1, tsig)          # primer minuto despues de la senal
        d = np.where(p.tipo == "W", 1, -1)
        neck = p.cuello.to_numpy()
        ext = np.where(d == -1, np.nanmax(p[["p_L1","p_L2","p_L3"]].to_numpy(), axis=1),
                                np.nanmin(p[["p_L1","p_L2","p_L3"]].to_numpy(), axis=1))
        for N in [2, 5]:
            hold = N * mins
            dir_pnl, fil_pnl, esperas = [], [], []
            for j in range(len(p)):
                e = k0[j]
                if e + hold + EXP * mins + 2 >= n1: continue
                dir_pnl.append(d[j] * (o1[e + hold] - o1[e]) - SP)
                # confirmacion: revisar velas M1 cerradas desde e-1 (la que termina en la senal)
                ent = -1
                for k in range(e - 1, e - 1 + EXP * mins):
                    if d[j] == -1 and h1[k] > ext[j]: break
                    if d[j] == 1 and l1[k] < ext[j]: break
                    a_favor = (c1[k] < o1[k]) if d[j] == -1 else (c1[k] > o1[k])
                    mas_alla = (c1[k] < neck[j]) if d[j] == -1 else (c1[k] > neck[j])
                    if a_favor and mas_alla and not salto[k]:
                        ent = k + 1; break
                if ent > 0:
                    fil_pnl.append(d[j] * (o1[ent + hold] - o1[ent]) - SP); esperas.append(ent - e)
            dp, fp = np.array(dir_pnl), np.array(fil_pnl)
            if len(dp) < 30: continue
            rows.append(dict(simbolo=s, tf=tf, N=N, n_directo=len(dp), pts_directo=dp.mean()/0.01,
                             acierto_directo=(dp>0).mean(), n_filtro=len(fp), pts_filtro=fp.mean()/0.01 if len(fp) else np.nan,
                             se_filtro=fp.std(ddof=1)/np.sqrt(len(fp))/0.01 if len(fp)>1 else np.nan,
                             acierto_filtro=(fp>0).mean() if len(fp) else np.nan,
                             espera_media_min=np.mean(esperas) if esperas else np.nan,
                             usd_dia_directo=dp.mean()/0.01/1000*len(dp)/dias,
                             usd_dia_filtro=(fp.mean()/0.01/1000*len(fp)/dias) if len(fp) else 0))
r = pd.DataFrame(rows); r.to_csv(sys.argv[2], index=False)
pd.set_option("display.width", 250)
print(r.round(2).to_string(index=False))
for N in [2, 5]:
    x = r[r.N == N]
    print(f"N={N}: DIRECTO {np.average(x.pts_directo, weights=x.n_directo):+.0f} pts/op, aciertos {np.average(x.acierto_directo, weights=x.n_directo):.1%}, $/dia {x.usd_dia_directo.sum():+.2f} | "
          f"FILTRO {np.average(x.pts_filtro, weights=x.n_filtro):+.0f} pts/op, aciertos {np.average(x.acierto_filtro, weights=x.n_filtro):.1%}, $/dia {x.usd_dia_filtro.sum():+.2f}, "
          f"entra en {x.n_filtro.sum()/x.n_directo.sum():.0%} de las senales | celdas filtro z>2: {((x.pts_filtro/x.se_filtro)>2).sum()}/{len(x)}")

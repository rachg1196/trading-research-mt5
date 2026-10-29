# -*- coding: utf-8 -*-
"""Estrategia 'seguir el tramo hasta el salto' (sin mirar al futuro), en velas M1:
 - Tras una vela con salto (rango > 4x mediana), mirar la vela siguiente (a+1): su direccion = direccion del tramo.
 - Si a+1 no tiene salto: entrar a favor del tramo en la apertura de a+2.
 - Mantener hasta que aparezca una vela con salto (b); salir en la apertura de la vela siguiente (b+1).
 - Coste: spread 130 pts (1.30). Opcional: costo extra de deslizamiento."""
import sys, numpy as np, pandas as pd
D = sys.argv[1]; SP = 1.30
for s in ["BreakX_600", "TrendX_600", "SwitchX_600"]:
    m = pd.read_parquet(f"{D}/{s}/M1.parquet"); m = m[m.time >= "2025-06-16"].reset_index(drop=True)
    t = m.time.to_numpy(); o, h, l, c = [m[k].to_numpy() for k in ["open","high","low","close"]]
    r = h - l; med = np.median(r); j = r > 4 * med; idx = np.where(j)[0]; n = len(o)
    rows = []
    for a, b in zip(idx[:-1], idx[1:]):
        e = a + 2
        if e > b or b + 1 >= n: continue          # salto en a+1: no se entra
        d = np.sign(c[a + 1] - o[a + 1])
        if d == 0: continue
        rows.append((t[e], d, d * (o[b + 1] - o[e]), b + 1 - e))
    df = pd.DataFrame(rows, columns=["t", "d", "bruto", "min"])
    df["neto"] = df.bruto - SP
    dias = (df.t.max() - df.t.min()) / np.timedelta64(1, "D")
    z = df.neto.mean() / (df.neto.std() / np.sqrt(len(df)))
    print(f"\n{s}: ops {len(df)} ({len(df)/dias:.0f}/dia) | bruto {df.bruto.mean()/0.01:+.0f} pts | NETO {df.neto.mean()/0.01:+.0f} pts | acierto {(df.neto>0).mean():.0%} | z {z:+.1f} | duracion media {df['min'].mean():.1f} min")
    # estabilidad: por mes y con costos extra
    mes = df.groupby(pd.to_datetime(df.t).dt.to_period("M")).neto.mean() / 0.01
    print("   neto por mes (pts):", " ".join(f"{k.strftime('%y-%m')}:{v:+.0f}" for k, v in mes.items()))
    for extra in [0.5, 1.0, 1.5, 2.0]:
        x = df.bruto - SP - extra
        print(f"   con {extra*100:.0f} pts extra de deslizamiento: neto {x.mean()/0.01:+.0f} pts")
    print(f"   USD/dia con lote 0.10 (sin limite de operaciones): {df.neto.mean()*0.10*len(df)/dias:+.2f}")

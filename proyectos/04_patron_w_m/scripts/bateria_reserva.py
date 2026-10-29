# -*- coding: utf-8 -*-
"""Bateria: reglas del EA Patron_WM_EA (W/M + confirmacion M1 + descarte 10 velas + salida N=2 velas)
en los 41 mercados y 12 temporalidades (datos de desarrollo, periodo en vivo), contra entradas al azar
con la misma salida. Coste = max(spread de la vela, spread actual). Lote 0.10 => 0.10 USD por 1.00 de precio."""
import os, sys, json, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector

D = sys.argv[1]; N = 2; EXP = 10; USD = 0.10; DESDE = pd.Timestamp(sys.argv[2]); OUTF = sys.argv[3]
MIN = {"M1":1,"M2":2,"M3":3}
RES = "/mnt/user-data/uploads/Desktop/proyecto w m/resultados"
spread_act = {}
for f in ["fase1_cortes.json", "mercados2_cortes.json", "mercados3_cortes.json"]:
    for s, v in json.load(open(os.path.join(RES, f)))["simbolos"].items():
        if "spread_ticks_pts" in v: spread_act[s.replace(" ", "_")] = v["spread_ticks_pts"]["mediana"]
rng = np.random.default_rng(41)
rows = []
for dd in sorted(glob.glob(f"{D}/*")):
    s = os.path.basename(dd); punto = 0.001 if s.startswith("MAX") else 0.01
    m1 = pd.read_parquet(f"{dd}/M1.parquet")
    t1 = m1.time.to_numpy(); o1, h1, l1, c1 = (m1[k].to_numpy() for k in ["open","high","low","close"])
    sp1 = np.maximum(m1.spread.to_numpy() * punto, spread_act.get(s, 0) * punto)
    rg = h1 - l1; salto = rg > 4 * np.median(rg) if np.median(rg) > 0 else np.zeros(len(rg), bool); n1 = len(m1)
    dias = (m1.time.iloc[-1] - DESDE).days
    for tf, mins in MIN.items():
        df = pd.read_parquet(f"{dd}/{tf}.parquet")
        if len(df) < 300: continue
        p = detector.detectar(df)
        hold = N * mins
        pnl = []
        if len(p):
            tsig = df.time.to_numpy()[p.i_senal.to_numpy()] + np.timedelta64(mins, "m")
            k0 = np.searchsorted(t1, tsig); d = np.where(p.tipo == "W", 1, -1); neck = p.cuello.to_numpy()
            pis = p[["p_L1","p_L2","p_L3"]].to_numpy()
            ext = np.where(d == -1, np.nanmax(pis, axis=1), np.nanmin(pis, axis=1))
            for j in range(len(p)):
                e = k0[j]
                if e < 2 or e + EXP * mins + hold + 2 >= n1: continue
                ent = -1
                for k in range(e - 1, e - 1 + EXP * mins):
                    if d[j] == -1 and h1[k] > ext[j]: break
                    if d[j] == 1 and l1[k] < ext[j]: break
                    fav = (c1[k] < o1[k]) if d[j] == -1 else (c1[k] > o1[k])
                    mas = (c1[k] < neck[j]) if d[j] == -1 else (c1[k] > neck[j])
                    if fav and mas and not salto[k]: ent = k + 1; break
                if ent < 0: continue
                if t1[ent] < np.datetime64(DESDE): continue
                pnl.append(d[j] * (o1[ent + hold] - o1[ent]) - sp1[ent])
        pnl = np.array(pnl)
        # azar: mismo numero (min 2000), misma salida
        i0 = np.searchsorted(t1, np.datetime64(DESDE)); nr = max(2000, len(pnl)); E = rng.integers(i0, n1 - hold - 2, nr); dr = rng.choice([1, -1], nr)
        pr = dr * (o1[E + hold] - o1[E]) - sp1[E]
        fila = dict(mercado=s.replace("_", " "), tf=tf, dias=dias, ops=len(pnl), ops_dia=len(pnl) / max(dias, 1),
                    azar_pts=pr.mean() / punto, spread_pts=np.median(sp1) / punto)
        if len(pnl) > 1:
            fila.update(acierto=(pnl > 0).mean(), pts_op=pnl.mean() / punto,
                        z=pnl.mean() / (pnl.std() / np.sqrt(len(pnl))),
                        z_vs_azar=(pnl.mean() - pr.mean()) / np.sqrt(pnl.var() / len(pnl) + pr.var() / len(pr)),
                        usd_dia=pnl.sum() * USD / max(dias, 1))
        rows.append(fila)
    print(s, "ok", flush=True)
r = pd.DataFrame(rows); r.to_csv(OUTF, index=False)
print("listo")

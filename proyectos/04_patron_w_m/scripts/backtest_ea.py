# -*- coding: utf-8 -*-
"""
BACKTEST del asesor Patron_WM_EA v2 con las reglas aprobadas por Raul.
 - Senal: cierre de vela mas alla del cuello (misma deteccion del indicador).
 - Confirmacion: ultima vela M1 cerrada a favor, sin salto y mas alla del cuello
   (aproximacion de los 30 s: los datos historicos no tienen segundos).
 - Descarte: 10 velas de la temporalidad sin confirmar, o rompe el techo (M) / piso (W).
 - Una sola entrada por senal. Entrada: apertura del minuto siguiente a la confirmacion.
 - Salida: N velas de la temporalidad desde la entrada (precio de apertura M1 en ese minuto).
 - Limites: 1 por mercado+temporalidad, max 3 por mercado, max 5 en total.
 - Coste: spread 130 puntos. Lote 0.10 -> 1.000 puntos = 1 USD.
Uso: python backtest_ea.py <datos> <salida> <N> <TFs separadas por coma> <etiqueta>
"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector

D, OUT, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
TFS = sys.argv[4].split(","); ETQ = sys.argv[5]
INI = pd.Timestamp("2025-06-16"); SP = 1.30; EXP = 10
MAX_MERCADO = int(sys.argv[6]) if len(sys.argv) > 6 else 3
MAX_TOTAL   = int(sys.argv[7]) if len(sys.argv) > 7 else 5
META_DIA    = float(sys.argv[8]) if len(sys.argv) > 8 else 0      # USD, 0 = sin meta
PERD_DIA    = float(sys.argv[9]) if len(sys.argv) > 9 else 0      # USD, 0 = sin limite
SIMS        = sys.argv[10].split(",") if len(sys.argv) > 10 else ["BreakX_600", "TrendX_600", "SwitchX_600"]
DESDE       = pd.Timestamp(sys.argv[11]) if len(sys.argv) > 11 else None   # solo entradas desde esta fecha (hora servidor)
USD_POR_PRECIO = 0.10            # lote 0.10: 1.00 de precio = 100 puntos = 0.10 USD
MIN = {"M1":1,"M2":2,"M3":3,"M4":4,"M5":5,"M6":6,"M10":10,"M12":12,"M15":15,"M20":20,"M30":30,"H1":60}

cand = []
for s in SIMS:
    m1 = pd.read_parquet(f"{D}/{s}/M1.parquet"); m1 = m1[m1.time >= INI].reset_index(drop=True)
    t1 = m1.time.to_numpy(); o1, h1, l1, c1 = (m1[k].to_numpy() for k in ["open","high","low","close"])
    rg = h1 - l1; salto = rg > 4 * np.median(rg); n1 = len(m1)
    for tf in TFS:
        mins = MIN[tf]
        df = pd.read_parquet(f"{D}/{s}/{tf}.parquet"); df = df[df.time >= INI].reset_index(drop=True)
        p = detector.detectar(df)
        if p.empty: continue
        tsig = df.time.to_numpy()[p.i_senal.to_numpy()] + np.timedelta64(mins, "m")
        k0 = np.searchsorted(t1, tsig)
        d = np.where(p.tipo == "W", 1, -1); neck = p.cuello.to_numpy()
        pis = p[["p_L1","p_L2","p_L3"]].to_numpy()
        ext = np.where(d == -1, np.nanmax(pis, axis=1), np.nanmin(pis, axis=1))
        hold = N * mins
        for j in range(len(p)):
            e = k0[j]
            if e + EXP * mins + hold + 2 >= n1: continue
            ent = -1
            for k in range(e - 1, e - 1 + EXP * mins):
                if d[j] == -1 and h1[k] > ext[j]: break
                if d[j] == 1 and l1[k] < ext[j]: break
                fav = (c1[k] < o1[k]) if d[j] == -1 else (c1[k] > o1[k])
                mas = (c1[k] < neck[j]) if d[j] == -1 else (c1[k] > neck[j])
                if fav and mas and not salto[k]:
                    ent = k + 1; break
            if ent < 0: continue
            pnl = d[j] * (o1[ent + hold] - o1[ent]) - SP
            cand.append(dict(simbolo=s.replace("_", " "), tf=tf, tipo="W" if d[j] == 1 else "M",
                             t_senal=tsig[j], t_entrada=t1[ent], t_salida=t1[ent + hold],
                             entrada=o1[ent], salida=o1[ent + hold], pnl_usd=pnl * USD_POR_PRECIO))

c = pd.DataFrame(cand).sort_values("t_entrada").reset_index(drop=True)
if DESDE is not None:
    c = c[pd.to_datetime(c.t_entrada) >= DESDE].reset_index(drop=True)

# aplicar limites de posiciones simultaneas, en orden cronologico
# (dia = hora de Ecuador = servidor - 8 h; el resultado del dia cuenta operaciones ya CERRADAS ese dia)
ECU = pd.Timedelta(hours=8)
abiertas, tomadas, paradas, por_dia = [], [], set(), {}
for _, r in c.iterrows():
    te = pd.Timestamp(r.t_entrada)
    abiertas = [a for a in abiertas if a[0] > r.t_entrada]
    if any(a[1] == r.simbolo and a[2] == r.tf for a in abiertas): continue
    if MAX_MERCADO > 0 and sum(a[1] == r.simbolo for a in abiertas) >= MAX_MERCADO: continue
    if MAX_TOTAL > 0 and len(abiertas) >= MAX_TOTAL: continue
    if META_DIA > 0 or PERD_DIA > 0:
        hoy = (te - ECU).date()
        pl = sum(v for ts, v in por_dia.get(hoy, []) if ts <= te)
        if (META_DIA > 0 and pl >= META_DIA) or (PERD_DIA > 0 and pl <= -PERD_DIA):
            paradas.add((hoy, "meta" if pl >= META_DIA > 0 else "perdida")); continue
    abiertas.append((r.t_salida, r.simbolo, r.tf)); tomadas.append(r)
    ts = pd.Timestamp(r.t_salida); por_dia.setdefault((ts - ECU).date(), []).append((ts, r.pnl_usd))
dias_meta = sum(1 for p in paradas if p[1] == "meta"); dias_perd = sum(1 for p in paradas if p[1] == "perdida")
print(f"dias detenido por meta: {dias_meta} | dias detenido por perdida maxima: {dias_perd}")
t = pd.DataFrame(tomadas).reset_index(drop=True)
t["hora_ecuador"] = (pd.to_datetime(t.t_entrada) - pd.Timedelta(hours=8))
t["dia"] = t.hora_ecuador.dt.date
t["equity"] = t.pnl_usd.cumsum()
t.to_csv(os.path.join(OUT, f"backtest_{ETQ}_operaciones.csv"), index=False)

dias = (pd.to_datetime(t.t_entrada).max() - pd.to_datetime(t.t_entrada).min()).days
gan, per = t[t.pnl_usd > 0], t[t.pnl_usd <= 0]
dd = (t.equity - t.equity.cummax()).min()
racha = mx = 0
for v in t.pnl_usd:
    racha = racha + 1 if v <= 0 else 0; mx = max(mx, racha)
diario = t.groupby("dia").pnl_usd.sum()
mensual = t.groupby(t.hora_ecuador.dt.to_period("M")).agg(ops=("pnl_usd", "size"), usd=("pnl_usd", "sum"),
                                                          aciertos=("pnl_usd", lambda x: (x > 0).mean()))
res = dict(etiqueta=ETQ, N=N, tfs=",".join(TFS), desde=str(t.t_entrada.min())[:10], hasta=str(t.t_entrada.max())[:10],
           dias=dias, senales_confirmadas=len(c), operaciones=len(t), ops_dia=len(t) / dias,
           aciertos=(t.pnl_usd > 0).mean(), ganancia_media=gan.pnl_usd.mean(), perdida_media=per.pnl_usd.mean(),
           neto_usd=t.pnl_usd.sum(), usd_dia=t.pnl_usd.sum() / dias, max_drawdown_usd=dd,
           peor_racha=mx, dias_positivos=(diario > 0).mean(), mejor_dia=diario.max(), peor_dia=diario.min())
pd.Series(res).to_csv(os.path.join(OUT, f"backtest_{ETQ}_resumen.csv"))
mensual.to_csv(os.path.join(OUT, f"backtest_{ETQ}_mensual.csv"))
por = t.groupby(["simbolo", "tf"]).agg(ops=("pnl_usd", "size"), aciertos=("pnl_usd", lambda x: (x > 0).mean()),
                                       usd=("pnl_usd", "sum")).reset_index()
por.to_csv(os.path.join(OUT, f"backtest_{ETQ}_por_mercado_tf.csv"), index=False)
for k, v in res.items():
    print(f"{k:>20}: {v:.3f}" if isinstance(v, float) else f"{k:>20}: {v}")
print(mensual.round(2).to_string())
print(por.round(2).to_string(index=False))

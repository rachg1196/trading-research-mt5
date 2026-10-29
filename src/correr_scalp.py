# -*- coding: utf-8 -*-
"""Backtest 3 estrategias scalping. Uso: python correr_wm.py SIMBOLO inicio fin_datos specs.json salida_dir
Solo usa datos de DESARROLLO (antes del inicio de la reserva)."""
import sys, os, json, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor, wm, scalp

SIM, INI, FIN, SPECS, OUT = sys.argv[1:6]
D = "datos/completo/"
TFS = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30", "H1"]
N_PRINCIPAL, N_INFO, K_AZAR, HORIZ, KS = 2, [1, 3, 5, 10], 2000, 20, [0.5, 1, 2, 3, 5]
os.makedirs(OUT, exist_ok=True)

sp = json.load(open(SPECS))[SIM]
ini, fin = pd.Timestamp(INI), pd.Timestamp(FIN)
corte = ini + 0.75 * (fin - ini)
m1 = motor.cargar_m1(D + f"{SIM}_M1.csv.gz", ini, corte, ajustar_splits="Stocks" in (sp.get("path") or ""))
punto = sp["point"]
# USD por 1 unidad de precio con lote minimo: de order_calc_profit (+1%) si existe; si no, del valor del tick
if sp.get("valor_1pct_lote_min") and sp.get("ask"):
    unidades = sp["valor_1pct_lote_min"] / (0.01 * sp["ask"])
else:
    unidades = sp["trade_tick_value"] / sp["trade_tick_size"] * sp["volume_min"]
# piso de spread = el mayor entre la mediana del ultimo anio de desarrollo y el spread actual (en % del precio)
ult = m1[m1.dt >= corte - pd.Timedelta(days=365)]
pct_dev = float((ult.spread * punto / ult.open).median())
# spread actual = mediana de las ultimas ~5 sesiones de velas M1 del archivo (solo coste, no resultados)
_c = pd.read_csv(D + f"{SIM}_M1.csv.gz", usecols=["open", "spread"]).tail(7000)
pct_hoy = float((_c.spread * punto / _c.open).median())
costes = dict(punto=punto, unidades=unidades, spread_pct=max(pct_dev, pct_hoy), swap_modo=sp["swap_mode"],
              swap_long=sp["swap_long"], swap_short=sp["swap_short"], swap_triple=sp["swap_rollover3days"])
costes15 = dict(costes, spread_pct=costes["spread_pct"] * 1.5)
info = dict(simbolo=SIM, inicio=str(ini), inicio_reserva=str(corte), velas_m1_desarrollo=len(m1),
            spread_pct_usado=costes["spread_pct"], spread_pct_dev=pct_dev, spread_pct_hoy=pct_hoy, unidades=unidades)
print(info, flush=True)

MAXJ = 1500
t_m1 = m1.time.to_numpy(); h_m1 = m1.high.to_numpy(); l_m1 = m1.low.to_numpy(); o_m1 = m1.open.to_numpy()
anio = m1.dt.dt.year.to_numpy()


from scipy.stats import norm
M = {"t": t_m1, "o": o_m1, "h": h_m1, "l": l_m1, "s": m1.spread.to_numpy()}
m5 = motor.armar_tf(m1, "M5"); m15 = motor.armar_tf(m1, "M15")
casos = [("E1 EMAs+RSI", "M5", m5, lambda: [(i, d, sl, None) for i, d, sl in scalp.e1(m5)]),
         ("E2 Donchian+EMA200", "M5", m5, lambda: [(i, d, sl, None) for i, d, sl in scalp.e2(m5, m15)]),
         ("E3 Rango asiatico", "M5", m5, lambda: scalp.e3(m5, 5)),
         ("E3 Rango asiatico", "M15", m15, lambda: scalp.e3(m15, 15))]
filas = []
rng = np.random.default_rng(9)
for nombre, tf, df, gen in casos:
    t0 = time.time(); per = motor.MIN[tf] * 60
    sen = gen(); tt = df.time.to_numpy()
    res = []
    for i, d, sl, med in sen:
        if i + 1 >= len(tt): continue
        r = scalp.ejecutar(tt[i] + per, d, sl, None, M, punto, unidades, costes["spread_pct"], med)
        if r: res.append(r)
    R = pd.DataFrame(res)
    for d, nom in [(1, "compras"), (-1, "ventas")]:
        base = dict(simbolo=SIM, estrategia=nombre, tf=tf, direccion=nom, senales=sum(1 for x in sen if x[1] == d))
        if len(R) == 0 or (R.d == d).sum() < 2:
            filas.append(dict(base, ops=0 if len(R) == 0 else int((R.d == d).sum()))); continue
        r = R[R.d == d].copy()
        # una operacion a la vez
        keep = []; libre = -1
        for k, row in r.sort_values("j").iterrows():
            if row.j >= libre: keep.append(k); libre = row.j + row.minutos
        r = r.loc[keep]
        sw = wm.costes_swap(t_m1[r.j.astype(int)], t_m1[r.j.astype(int)] + r.minutos.to_numpy() * 60, r.pe.to_numpy(), np.full(len(r), d), costes)
        neto = r.neto.to_numpy() + sw; med = neto.mean()
        # azar: mismas distancias de SL/TP y direccion, entrada al azar
        K = 200; medias = np.empty(K); pares = r[["sl_dist", "tp_dist"]].to_numpy()
        for k in range(K):
            js = rng.integers(0, len(t_m1) - MAXJ, len(r)); acc = []
            for jj, (sd, tdist) in zip(js, pares):
                pe = o_m1[jj]; spr = max(M["s"][jj] * punto, costes["spread_pct"] * pe)
                slv = pe - d * (sd - 10 * punto)
                x = scalp.ejecutar(t_m1[jj], d, slv, None, M, punto, unidades, costes["spread_pct"])
                if x is None: continue
                acc.append(x["neto"])
            medias[k] = np.mean(acc) if acc else np.nan
        medias = medias[~np.isnan(medias)]
        p_norm = float(norm.sf((med - medias.mean()) / medias.std())) if len(medias) > 10 and medias.std() > 0 else 1.0
        an = pd.Series(neto, index=anio[r.j.astype(int)]).groupby(level=0).sum()
        eq = np.cumsum(neto); dd = float((np.maximum.accumulate(eq) - eq).max())
        gan = neto[neto > 0].sum(); per_ = -neto[neto < 0].sum()
        r15 = neto - 0.5 * r.spread.to_numpy()
        filas.append(dict(base, ops=len(r), aciertos_pct=round(100 * (neto > 0).mean(), 1), usd_total=round(neto.sum(), 2),
            usd_por_op=round(med, 4), bruto_por_op=round(r.bruto.mean(), 4), spread_por_op=round(r.spread.mean(), 4),
            profit_factor=round(gan / per_, 3) if per_ > 0 else np.nan, pct_tp=round(100 * (r.motivo == "tp").mean(), 1),
            pct_sl=round(100 * (r.motivo == "sl").mean(), 1), minutos_media=round(r.minutos.mean(), 1),
            sl_usd_medio=round((r.sl_dist * unidades).mean(), 3), tp_usd_medio=round((r.tp_dist * unidades).mean(), 3),
            peor_caida_usd=round(dd, 2), azar_media=round(float(medias.mean()), 4) if len(medias) else np.nan, p_normal=p_norm,
            anios_positivos=f"{int((an > 0).sum())}/{len(an)}", anios_pos_frac=float((an > 0).mean()),
            usd_por_op_spread15=round(r15.mean(), 4)))
    print(nombre, tf, len(sen), "senales", f"{time.time() - t0:.0f}s", flush=True)
tab = pd.DataFrame(filas)
tab.to_csv(os.path.join(OUT, f"scalp_{SIM}.csv"), index=False)
print(tab.drop(columns=["simbolo"]).to_string())

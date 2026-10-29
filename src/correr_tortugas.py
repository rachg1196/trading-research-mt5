# -*- coding: utf-8 -*-
"""Backtest Tortugas/Donchian. Uso: python correr_wm.py SIMBOLO inicio fin_datos specs.json salida_dir
Solo usa datos de DESARROLLO (antes del inicio de la reserva)."""
import sys, os, json, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor, wm, tortugas

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

t_m1 = m1.time.to_numpy(); h_m1 = m1.high.to_numpy(); l_m1 = m1.low.to_numpy(); o_m1 = m1.open.to_numpy()
anio = m1.dt.dt.year.to_numpy()


from scipy.stats import norm
VARIANTES = [("S1 20/10", 20, 10, False), ("S1 20/10 + filtro", 20, 10, True), ("S2 55/20", 55, 20, False)]
filas = []
for tf in TFS:
    t0 = time.time()
    tfdf = motor.armar_tf(m1, tf); per = motor.MIN[tf] * 60
    for nombre, ne, ns, filt in VARIANTES:
        for dire, nom in [(1, "compras"), (-1, "ventas")]:
            ops = tortugas.operaciones(tfdf, ne, ns, dire)
            if filt: ops = tortugas.filtro_s1(ops)
            base = dict(simbolo=SIM, tf=tf, variante=nombre, direccion=nom)
            if len(ops) < 2:
                filas.append(dict(base, ops=len(ops))); continue
            tt = tfdf.time.to_numpy()
            te = tt[ops.i_ent.to_numpy()]; ts = tt[ops.i_sal.to_numpy()] + per // 2   # salida a media vela
            je = np.minimum(np.searchsorted(t_m1, te), len(t_m1) - 1)
            bruto = (ops.p_sal - ops.p_ent).to_numpy() * dire * unidades
            def costes_de(cst):
                spr = np.maximum(m1.spread.to_numpy()[je] * punto, cst["spread_pct"] * ops.p_ent.abs().to_numpy()) * unidades
                sw = wm.costes_swap(te, ts, ops.p_ent.abs().to_numpy(), np.full(len(ops), dire), cst)
                return spr, sw
            spr, sw = costes_de(costes); neto = bruto - spr + sw
            spr15, sw15 = costes_de(costes15); neto15 = bruto - spr15 + sw15
            med = neto.mean()
            # azar: mismas duraciones y direccion, entradas al azar, mismos costes
            dur = ts - te; rng = np.random.default_rng(3); K = 500; medias = np.empty(K)
            o = o_m1; sp_m1 = m1.spread.to_numpy() * punto
            for k in range(K):
                j = rng.integers(0, len(t_m1) - 1, len(ops)); d = rng.permutation(dur)
                js = np.minimum(np.searchsorted(t_m1, t_m1[j] + d), len(t_m1) - 1)
                b = (o[js] - o[j]) * dire * unidades
                sp_ = np.maximum(sp_m1[j], costes["spread_pct"] * o[j]) * unidades
                sw_ = wm.costes_swap(t_m1[j], t_m1[j] + d, o[j], np.full(len(j), dire), costes)
                medias[k] = np.mean(b - sp_ + sw_)
            p = (np.sum(medias >= med) + 1) / (K + 1)
            p_norm = float(norm.sf((med - medias.mean()) / medias.std())) if medias.std() > 0 else 1.0
            an = pd.Series(neto, index=anio[je]).groupby(level=0).sum()
            eq = np.cumsum(neto); dd = float((np.maximum.accumulate(eq) - eq).max())
            filas.append(dict(base, ops=len(ops), aciertos_pct=round(100 * (neto > 0).mean(), 1), usd_total=round(neto.sum(), 2),
                usd_por_op=round(med, 4), bruto_por_op=round(bruto.mean(), 4), spread_por_op=round(spr.mean(), 4),
                swap_por_op=round(sw.mean(), 4), velas_media=round(float((ops.i_sal - ops.i_ent).mean()), 1),
                horas_media=round(float(dur.mean() / 3600), 1), peor_caida_usd=round(dd, 2), azar_media=round(float(medias.mean()), 4),
                p=p, p_normal=p_norm, anios_positivos=f"{int((an > 0).sum())}/{len(an)}", anios_pos_frac=float((an > 0).mean()),
                usd_por_op_spread15=round(neto15.mean(), 4), pct_stop=round(100 * (ops.motivo == "stop").mean(), 1)))
    print(tf, f"{time.time() - t0:.0f}s", flush=True)
tab = pd.DataFrame(filas)
tab.to_csv(os.path.join(OUT, f"tortugas_{SIM}.csv"), index=False)
json.dump(info, open(os.path.join(OUT, f"info_tortugas_{SIM}.json"), "w"), indent=1)
print(tab.drop(columns=["simbolo"]).to_string())

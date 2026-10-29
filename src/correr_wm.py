# -*- coding: utf-8 -*-
"""Backtest W y M (plan aprobado). Uso: python correr_wm.py SIMBOLO inicio fin_datos specs.json salida_dir
Solo usa datos de DESARROLLO (antes del inicio de la reserva)."""
import sys, os, json, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor, wm, detector

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


def recorrido(ent_idx, tipos, atr_val, tf):
    """Para cada entrada: max a favor y en contra en las HORIZ velas siguientes (en ATR), vela del mejor punto,
    y para cada k si toco +k ATR antes que -k ATR."""
    per = motor.MIN[tf] * 60
    res = []
    for e, tp, a in zip(ent_idx, tipos, atr_val):
        b = np.searchsorted(t_m1, t_m1[e] + HORIZ * per)
        if b >= len(t_m1) or a <= 0:
            continue
        pe = o_m1[e]
        fav = ((h_m1[e:b] - pe) if tp == 1 else (pe - l_m1[e:b])) / a
        con = ((pe - l_m1[e:b]) if tp == 1 else (h_m1[e:b] - pe)) / a
        cf = np.maximum.accumulate(fav); cc = np.maximum.accumulate(con)
        fila = dict(mfe=cf[-1], mae=cc[-1], vela_mejor=int((t_m1[e + int(np.argmax(fav))] - t_m1[e]) // per) + 1)
        for k in KS:
            jf = np.argmax(cf >= k) if cf[-1] >= k else 10**9
            jc = np.argmax(cc >= k) if cc[-1] >= k else 10**9
            fila[f"llega_{k}"] = cf[-1] >= k
            fila[f"antes_{k}"] = jf < jc            # +k antes que -k (si son la misma vela M1 cuenta como perdida)
        res.append(fila)
    return pd.DataFrame(res)


filas, rec_filas = [], []
for tf in TFS:
    t0 = time.time()
    tfdf = motor.armar_tf(m1, tf)
    sen = wm.senales(tfdf)
    sen = wm.confirmar(sen, tfdf, tf, m1, punto)
    atr_tf = detector.atr(tfdf.high.to_numpy(float), tfdf.low.to_numpy(float), tfdf.close.to_numpy(float), 14)
    sen["atr"] = atr_tf[sen.i_senal.to_numpy()]
    for dire, nom in [(1, "compras (W)"), (-1, "ventas (M)")]:
        s = sen[sen.tipo == dire].sort_values("j_ent").drop_duplicates("j_ent")
        base = dict(simbolo=SIM, tf=tf, direccion=nom, senales=len(s))
        if len(s) == 0:
            filas.append(dict(base, ops=0)); continue
        r = wm.simular(s.j_ent.to_numpy(), s.tipo.to_numpy(), m1, tf, N_PRINCIPAL, costes)
        if len(r) == 0:
            filas.append(dict(base, ops=0)); continue
        r15 = wm.simular(s.j_ent.to_numpy(), s.tipo.to_numpy(), m1, tf, N_PRINCIPAL, costes15)
        med = r.neto.mean()
        az = wm.azar(m1, tf, N_PRINCIPAL, r.tipo.to_numpy(), costes, K=K_AZAR)
        p = (np.sum(az >= med) + 1) / (K_AZAR + 1)
        from scipy.stats import norm
        p_norm = float(norm.sf((med - az.mean()) / az.std())) if az.std() > 0 else 1.0
        an = pd.Series(r.neto.to_numpy(), index=anio[r.j_ent]).groupby(level=0).sum()
        eq = r.neto.cumsum(); dd = float((eq.cummax() - eq).max())
        fila = dict(base, ops=len(r), aciertos_pct=round(100 * (r.neto > 0).mean(), 1), usd_total=round(r.neto.sum(), 2),
                    usd_por_op=round(med, 4), bruto_por_op=round(r.bruto.mean(), 4), spread_por_op=round(r.spread.mean(), 4),
                    swap_por_op=round(r.swap.mean(), 4), peor_caida_usd=round(dd, 2), azar_media=round(float(az.mean()), 4),
                    p=p, p_normal=p_norm, azar_std=float(az.std()), anios_positivos=f"{int((an > 0).sum())}/{len(an)}", anios_pos_frac=float((an > 0).mean()),
                    usd_por_op_spread15=round(r15.neto.mean(), 4))
        for n in N_INFO:
            ri = wm.simular(s.j_ent.to_numpy(), s.tipo.to_numpy(), m1, tf, n, costes)
            fila[f"usd_por_op_N{n}"] = round(ri.neto.mean(), 4) if len(ri) else np.nan
        filas.append(fila)
        # recorrido: estrategia y azar (mismo numero de entradas al azar)
        atr_e = s.set_index("j_ent").loc[r.j_ent, "atr"].to_numpy()
        rc = recorrido(r.j_ent.to_numpy(), r.tipo.to_numpy(), atr_e, tf)
        rng = np.random.default_rng(11)
        ja = rng.choice(len(t_m1) - 1, min(len(r) * 3, 20000), replace=True)
        # ATR al azar: el ATR de la vela TF vigente
        itf = np.searchsorted(tfdf.time.to_numpy(), t_m1[ja], side="right") - 1
        ra = recorrido(ja, np.full(len(ja), dire), atr_tf[np.maximum(itf, 0)], tf)
        for nombre, df_ in [("estrategia", rc), ("azar", ra)]:
            if len(df_) == 0: continue
            d = dict(simbolo=SIM, tf=tf, direccion=nom, grupo=nombre, n=len(df_),
                     mfe_mediana_atr=round(df_.mfe.median(), 2), mae_mediana_atr=round(df_.mae.median(), 2),
                     vela_mejor_mediana=float(df_.vela_mejor.median()))
            for k in KS:
                d[f"llega_{k}ATR_pct"] = round(100 * df_[f"llega_{k}"].mean(), 1)
                d[f"tp{k}_antes_sl{k}_pct"] = round(100 * df_[f"antes_{k}"].mean(), 1)
            rec_filas.append(d)
    print(tf, f"{time.time() - t0:.0f}s", flush=True)

tab = pd.DataFrame(filas)
tab.to_csv(os.path.join(OUT, f"wm_{SIM}.csv"), index=False)
pd.DataFrame(rec_filas).to_csv(os.path.join(OUT, f"recorrido_{SIM}.csv"), index=False)
json.dump(info, open(os.path.join(OUT, f"info_{SIM}.json"), "w"), indent=1)
print(tab.to_string())

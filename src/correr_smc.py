# -*- coding: utf-8 -*-
"""Backtest SMC (PLAN_SMC.md). Uso: python correr_smc.py SIM INI FIN [specs] [salida]"""
import sys, os, json, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor as mt, wm
from smc_nb import motor, simular2, atr_sma
from scipy.stats import norm

SIM, INI, FIN = sys.argv[1:4]
SPECS = sys.argv[4] if len(sys.argv) > 4 else "config/specs_todos.json"
OUT = sys.argv[5] if len(sys.argv) > 5 else "resultados"
D = os.environ.get("DATOS", "datos/completo/")
sp = json.load(open(SPECS))[SIM]
ini, fin = pd.Timestamp(INI), pd.Timestamp(FIN); corte = ini + 0.75 * (fin - ini)
m1 = mt.cargar_m1(D + f"{SIM}_M1.csv.gz", ini, corte)
punto = sp["point"]; unidades = sp["valor_1pct_lote_min"] / (0.01 * sp["ask"])
ult = m1[m1.dt >= corte - pd.Timedelta(days=365)]
_c = pd.read_csv(D + f"{SIM}_M1.csv.gz", usecols=["open", "spread"]).tail(7000)
spct = max(float((ult.spread * punto / ult.open).median()), float((_c.spread * punto / _c.open).median()))
costes = dict(punto=punto, unidades=unidades, spread_pct=spct, swap_modo=sp["swap_mode"], swap_long=sp["swap_long"],
              swap_short=sp["swap_short"], swap_triple=sp["swap_rollover3days"])
T = m1.time.to_numpy(np.int64); O = m1.open.to_numpy(float); H = m1.high.to_numpy(float)
L = m1.low.to_numpy(float); S = m1.spread.to_numpy(float) * punto
anio = m1.dt.dt.year.to_numpy()
semanas = (corte - ini).days / 7
MAXV = 500


def sin_solape(je, js):
    orden = np.argsort(je, kind="stable"); keep = []; libre = -1
    for r in orden:
        if je[r] >= libre: keep.append(r); libre = js[r]
    return np.array(keep, int)


def resumen(base, je, js, pe, ps, spr, d, sel, az):
    r = np.nonzero(sel & (je >= 0))[0]
    r = r[sin_solape(je[r], js[r])] if len(r) else r
    if len(r) < 2: return dict(base, ops=len(r))
    neto = (ps[r] - pe[r]) * d * unidades - spr[r]
    neto = neto + wm.costes_swap(T[je[r]], T[js[r]], pe[r], np.full(len(r), d), costes)
    med = neto.mean(); se = np.sqrt(neto.var() / len(neto) + az.var() / len(az))
    p = float(norm.sf((med - az.mean()) / se)) if se > 0 else 1.0
    an = pd.Series(neto, index=anio[je[r]]).groupby(level=0).sum()
    eq = np.cumsum(neto[np.argsort(je[r])])
    return dict(base, ops=len(r), aciertos_pct=round(100 * (neto > 0).mean(), 1), usd_por_op=round(med, 4),
                usd_total=round(neto.sum(), 2), spread_usd=round(float(spr[r].mean()), 4),
                peor_caida_usd=round(float((np.maximum.accumulate(eq) - eq).max()), 2),
                minutos_medios=round(float((T[js[r]] - T[je[r]]).mean() / 60), 1),
                azar_media=round(float(az.mean()), 4), p_normal=p,
                anios_positivos=f"{int((an > 0).sum())}/{len(an)}", anios_pos_frac=float((an > 0).mean()),
                usd_por_op_spread15=round(float((neto - 0.5 * spr[r]).mean()), 4),
                ops_por_semana=round(len(r) / semanas, 2))


filas = []
for tf in ["M1", "M5", "M15", "H1"]:
    t0 = time.time()
    g = mt.armar_tf(m1, tf); per = mt.MIN[tf] * 60
    tt = g.time.to_numpy(np.int64)
    o, h, l, c = (g[x].to_numpy(float) for x in ["open", "high", "low", "close"])
    a14 = atr_sma(h, l, c, 14)
    rint, choch, rsw, tsw, obi, obd, obv, fvi, fvd, fvv = motor(o, h, l, c)
    nb = len(tt)
    # proxima ruptura interna opuesta (para la salida X1)
    sig_up = np.nonzero(rint == 1)[0]; sig_dn = np.nonzero(rint == -1)[0]

    def prox_opuesta(i, d):
        arr = sig_dn if d == 1 else sig_up
        k = np.searchsorted(arr, i, side="right")
        j = arr[k] if k < len(arr) else nb - 1
        return min(j, i + MAXV, nb - 1)

    # --- senales: (vela, dir, nivel, es_limite, tipo)
    sen = {}
    ib = np.nonzero(rint != 0)[0]
    sen["RUPT_INT"] = (ib, rint[ib], False)
    ch = ib[choch[ib]]; bo = ib[~choch[ib]]
    sen["CHOCH_INT"] = (ch, rint[ch], False)
    sen["BOS_INT"] = (bo, rint[bo], False)
    sb = np.nonzero(rsw != 0)[0]
    sen["RUPT_SWING"] = (sb, rsw[sb], False)
    sen["OB_RETEST"] = (obi, obd, True, obv)
    sen["FVG_RETEST"] = (fvi, fvd, True, fvv)

    for nombre, v in sen.items():
        idx, dirs, lim = v[0], v[1], v[2]
        niv = v[3] if lim else np.zeros(len(idx))
        if len(idx) == 0: continue
        ok = (idx < nb - 2)
        idx, dirs, niv = idx[ok], dirs[ok], niv[ok]
        if lim:
            ent0 = tt[idx]; ent1 = tt[idx] + per; atrv = a14[np.maximum(idx - 1, 0)]
            ref = np.maximum(idx - 1, 0)            # tendencia swing conocida antes de la vela
        else:
            ent0 = tt[idx] + per; ent1 = ent0 + 60; atrv = a14[idx]; ref = idx
        filtro_sw = tsw[ref] == dirs
        for d in (1, -1):
            md = dirs == d
            if md.sum() < 2: continue
            for xn in ("X1_raul", "X2_fijo"):
                if xn == "X1_raul":
                    sld = np.zeros(md.sum()); tpd = 2 * atrv[md]
                    tsal = np.array([tt[prox_opuesta(i, d)] + per for i in idx[md]])
                else:
                    sld = 2 * atrv[md]; tpd = 2 * atrv[md]
                    tsal = tt[np.minimum(idx[md] + MAXV, nb - 1)]
                je, js, pe, ps, spr = simular2(T, O, H, L, S, ent0[md], ent1[md], np.full(md.sum(), d, np.int64),
                                               niv[md], sld, tpd, tsal, spct, unidades, lim)
                # azar con la misma salida
                rng = np.random.default_rng(7 + d + (xn == "X2_fijo"))
                jr = rng.integers(0, len(T) - 5000, 3000)
                br = np.clip(np.searchsorted(tt, T[jr], side="right") - 1, 1, nb - 3)
                if xn == "X1_raul":
                    asl = np.zeros(3000); atp = 2 * a14[br]
                    atsal = np.array([tt[prox_opuesta(i, d)] + per for i in br])
                else:
                    asl = 2 * a14[br]; atp = 2 * a14[br]; atsal = tt[np.minimum(br + MAXV, nb - 1)]
                aje, ajs, ape, aps, aspr = simular2(T, O, H, L, S, T[jr], T[jr] + 60, np.full(3000, d, np.int64),
                                                    np.zeros(3000), asl, atp, atsal, spct, unidades, False)
                v_ = aje >= 0
                az = (aps[v_] - ape[v_]) * d * unidades - aspr[v_]
                az = az + wm.costes_swap(T[aje[v_]], T[ajs[v_]], ape[v_], np.full(v_.sum(), d), costes)
                for fn, fsel in (("sin filtro", np.ones(md.sum(), bool)), ("a favor swing", filtro_sw[md])):
                    base = dict(simbolo=SIM, tf=tf, senal=nombre, filtro=fn, salida=xn,
                                direccion="compras" if d == 1 else "ventas")
                    filas.append(resumen(base, je, js, pe, ps, spr, d, fsel, az))
    print(tf, f"{time.time() - t0:.0f}s", flush=True)

tab = pd.DataFrame(filas)
os.makedirs(OUT, exist_ok=True)
tab.to_csv(f"{OUT}/smc_{SIM}.csv", index=False)
print(tab[["tf", "senal", "filtro", "salida", "direccion", "ops", "aciertos_pct", "usd_por_op", "azar_media", "p_normal"]].to_string())

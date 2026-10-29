# -*- coding: utf-8 -*-
"""Backtest lineas tipo Joel (PLAN_LINEAS_JOEL.md). Uso: python correr_lineas.py SIM INI FIN [specs] [salida]"""
import sys, os, json, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor, wm
from lineas_nb import pivotes, toques_bajistas, pierna, simular
from scipy.stats import norm

SIM, INI, FIN = sys.argv[1:4]
SPECS = sys.argv[4] if len(sys.argv) > 4 else "config/specs_todos.json"
OUT = sys.argv[5] if len(sys.argv) > 5 else "resultados"
D = os.environ.get("DATOS", "datos/completo/")
sp = json.load(open(SPECS))[SIM]
ini, fin = pd.Timestamp(INI), pd.Timestamp(FIN); corte = ini + 0.75 * (fin - ini)
m1 = motor.cargar_m1(D + f"{SIM}_M1.csv.gz", ini, corte)
punto = sp["point"]; unidades = sp["valor_1pct_lote_min"] / (0.01 * sp["ask"])
ult = m1[m1.dt >= corte - pd.Timedelta(days=365)]
_c = pd.read_csv(D + f"{SIM}_M1.csv.gz", usecols=["open", "spread"]).tail(7000)
spct = max(float((ult.spread * punto / ult.open).median()), float((_c.spread * punto / _c.open).median()))
costes = dict(punto=punto, unidades=unidades, spread_pct=spct, swap_modo=sp["swap_mode"], swap_long=sp["swap_long"],
              swap_short=sp["swap_short"], swap_triple=sp["swap_rollover3days"])
T = m1.time.to_numpy(np.int64); O = m1.open.to_numpy(float); H = m1.high.to_numpy(float)
L = m1.low.to_numpy(float); S = m1.spread.to_numpy(float) * punto
anio = m1.dt.dt.year.to_numpy()

TFS = ["M2", "M3", "M5", "M6", "M10", "M15", "M20", "M30", "H1"]
MAYOR = {tf: ("H1" if motor.MIN[tf] <= 15 else "H4") for tf in TFS}
VAR_T = {"toques 3-4": (3, 4), "toques 3-6": (3, 6)}


def atr_prev(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    a = pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    return np.r_[a[0], a[:-1]]


def sin_solape(je, js):
    orden = np.argsort(je, kind="stable"); keep = []; libre = -1
    for r in orden:
        if je[r] >= libre: keep.append(r); libre = js[r]
    return np.array(keep, int)


piernas = {}
for tfm in ["H1", "H4"]:
    g = motor.armar_tf(m1, tfm)
    h, l, c = (g[x].to_numpy(float) for x in ["high", "low", "close"])
    ph, pl = pivotes(h, l)
    piernas[tfm] = (g.time.to_numpy(np.int64) + motor.MIN[tfm] * 60, pierna(h, l, c, ph, pl))  # (hora de cierre, estado)

filas = []
for tf in TFS:
    t0 = time.time()
    g = motor.armar_tf(m1, tf); per = motor.MIN[tf] * 60
    tt = g.time.to_numpy(np.int64)
    o, h, l, c = (g[x].to_numpy(float) for x in ["open", "high", "low", "close"])
    ap = atr_prev(h, l, c)
    ph, pl = pivotes(h, l)
    phm, plm = pivotes(-l, -h)       # espejo para compras
    tc, est = piernas[MAYOR[tf]]
    k = np.searchsorted(tc, tt, side="right") - 1          # ultima vela mayor cerrada al abrir la vela tf
    dir_mayor = np.where(k >= 0, est[np.maximum(k, 0)], 0)
    for d in (-1, 1):
        if d == -1: bi, bt, bv = toques_bajistas(h, l, c, ap, ph, pl)
        else:
            bi, bt, bv = toques_bajistas(-l, -h, -c, ap, phm, plm); bv = -bv
        ok = dir_mayor[bi] == d
        bi, bt, bv = bi[ok], bt[ok], bv[ok]
        for nv in (1, 2):
            n = len(bi)
            je, js, pe, ps, spr = simular(T, O, H, L, S, tt[bi], tt[bi] + per, np.full(n, d, np.int64), bv,
                                          ap[bi], tt[bi] + nv * per, spct, unidades, True)
            # azar: 3000 minutos al azar, misma salida (fin de la vela tf que lo contiene + nv-1), mismo SL
            rng = np.random.default_rng(11 + nv + (d > 0))
            jr = rng.integers(0, len(T) - 5000, 3000)
            br = np.clip(np.searchsorted(tt, T[jr], side="right") - 1, 1, len(tt) - 1)
            aje, ajs, ape, aps, aspr = simular(T, O, H, L, S, T[jr], T[jr] + 60, np.full(3000, d, np.int64), np.zeros(3000),
                                               ap[br], tt[br] + nv * per, spct, unidades, False)
            az = (aps - ape) * d * unidades - aspr
            az = az + wm.costes_swap(T[aje], T[ajs], ape, np.full(3000, d), costes)
            for vn, (t1, t2) in VAR_T.items():
                sel = (je >= 0) & (bt >= t1) & (bt <= t2)
                r = np.nonzero(sel)[0]
                r = r[sin_solape(je[r], js[r])] if len(r) else r
                base = dict(simbolo=SIM, tf=tf, mayor=MAYOR[tf], direccion="compras" if d == 1 else "ventas",
                            toques=vn, salida=f"{nv} vela" + ("s" if nv > 1 else ""))
                if len(r) < 2:
                    filas.append(dict(base, ops=len(r))); continue
                neto = (ps[r] - pe[r]) * d * unidades - spr[r]
                neto = neto + wm.costes_swap(T[je[r]], T[js[r]], pe[r], np.full(len(r), d), costes)
                med = neto.mean()
                se = np.sqrt(neto.var() / len(neto) + az.var() / len(az))
                p = float(norm.sf((med - az.mean()) / se)) if se > 0 else 1.0
                an = pd.Series(neto, index=anio[je[r]]).groupby(level=0).sum()
                eq = np.cumsum(neto[np.argsort(je[r])])
                filas.append(dict(base, ops=len(r), aciertos_pct=round(100 * (neto > 0).mean(), 1),
                                  usd_por_op=round(med, 4), usd_total=round(neto.sum(), 2),
                                  sl_usd=round(float((ap[bi[r]] * unidades).mean()), 3),
                                  spread_usd=round(float(spr[r].mean()), 4),
                                  peor_caida_usd=round(float((np.maximum.accumulate(eq) - eq).max()), 2),
                                  azar_media=round(float(az.mean()), 4), p_normal=p,
                                  anios_positivos=f"{int((an > 0).sum())}/{len(an)}", anios_pos_frac=float((an > 0).mean()),
                                  usd_por_op_spread15=round(float((neto - 0.5 * spr[r]).mean()), 4),
                                  ops_por_semana=round(len(r) / ((corte - ini).days / 7), 2)))
    print(tf, f"{time.time() - t0:.0f}s", flush=True)

tab = pd.DataFrame(filas)
os.makedirs(OUT, exist_ok=True)
tab.to_csv(f"{OUT}/lineas_{SIM}.csv", index=False)
print(tab.drop(columns=["simbolo", "p_normal", "anios_pos_frac"], errors="ignore").to_string())

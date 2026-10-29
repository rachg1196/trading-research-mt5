import sys, json, numpy as np, pandas as pd
from scipy.stats import t as tdist
sys.path.insert(0, "src")
import motor as mt, wm
from smc_nb import motor, simular2, atr_sma
SIM, DESDE, HASTA = sys.argv[1:4]
D = "datos/sinteticos/"; sp = json.load(open("config/specs_sint2.json"))[SIM]
m1 = mt.cargar_m1(D + f"{SIM}_M1.csv.gz", DESDE, HASTA)
punto = sp["point"]; un = sp["valor_1pct_lote_min"] / (0.01 * sp["ask"])
costes = dict(punto=punto, unidades=un, spread_pct=0.0, swap_modo=1, swap_long=sp["swap_long"], swap_short=sp["swap_short"], swap_triple=sp["swap_rollover3days"])
T = m1.time.to_numpy(np.int64); O = m1.open.to_numpy(float); H = m1.high.to_numpy(float); L = m1.low.to_numpy(float)
S = m1.spread.to_numpy(float) * punto
o, h, l, c = (m1[x].to_numpy(float) for x in ["open", "high", "low", "close"]); tt = T
a14 = atr_sma(h, l, c, 14); rint = motor(o, h, l, c)[0]
filas = []
for d in (1, -1):
    idx = np.nonzero(rint == d)[0]; idx = idx[idx < len(tt) - 600]
    res = {}
    for ms in (1, 2):
        e0 = tt[idx] + 60
        je, js, pe, ps, spr = simular2(T, O, H, L, S * ms, e0, e0 + 60, np.full(len(idx), d, np.int64), np.zeros(len(idx)),
                                       2 * a14[idx], 2 * a14[idx], tt[idx + 500], 0.0, un, False)
        keep = []; libre = -1
        for r in np.argsort(je):
            if je[r] >= 0 and je[r] >= libre: keep.append(r); libre = js[r]
        keep = np.array(keep, int)
        neto = (ps[keep] - pe[keep]) * d * un - spr[keep] + wm.costes_swap(T[je[keep]], T[js[keep]], pe[keep], np.full(len(keep), d), costes)
        res[ms] = (keep, neto)
    keep, neto = res[1]
    mes = pd.Series(neto, index=pd.to_datetime(T[je[keep]] if False else T[np.array([0])], unit="s")) if False else None
    meses = pd.Series(neto, index=pd.to_datetime(tt[idx[keep]], unit="s").to_period("M")).groupby(level=0).sum()
    tv = neto.mean() / (neto.std(ddof=1) / np.sqrt(len(neto)))
    filas.append(dict(mercado=SIM, direccion="compras" if d == 1 else "ventas", ops=len(neto),
                      aciertos=round(100 * (neto > 0).mean(), 1), usd_op=round(neto.mean(), 4), usd_total=round(neto.sum(), 1),
                      p=float(tdist.sf(tv, len(neto) - 1)), meses_pos=f"{int((meses > 0).sum())}/{len(meses)}",
                      meses_frac=float((meses > 0).mean()), usd_op_spread2=round(res[2][1].mean(), 4),
                      sl_medio_puntos=round(float((2 * a14[idx]).mean() / punto)), stops_level=sp["stops_level"]))
print(json.dumps(filas))

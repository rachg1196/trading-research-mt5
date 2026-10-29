import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "src")
import motor as mt
from smc_nb import motor, simular2, atr_sma
D = "datos/sinteticos_v1/"; SIM = "BreakX600"
sp = json.load(open("config/specs_sint.json"))[SIM]
ini, fin = pd.Timestamp("2025-01-02"), pd.Timestamp("2026-10-18"); corte = ini + 0.75 * (fin - ini)
desde, hasta = (ini, corte) if sys.argv[1] == "dev" else (corte, fin)
m1 = mt.cargar_m1(D + f"{SIM}_M1.csv.gz", desde, hasta)
punto = sp["point"]; un = sp["valor_1pct_lote_min"] / (0.01 * sp["ask"])
T = m1.time.to_numpy(np.int64); O = m1.open.to_numpy(float); H = m1.high.to_numpy(float); L = m1.low.to_numpy(float)
S = m1.spread.to_numpy(float) * punto
g = mt.armar_tf(m1, "M1"); tt = g.time.to_numpy(np.int64)
o, h, l, c = (g[x].to_numpy(float) for x in ["open", "high", "low", "close"])
a14 = atr_sma(h, l, c, 14)
rint = motor(o, h, l, c)[0]
print(sys.argv[1], desde.date(), hasta.date(), "| velas", len(tt), "| ATR14 medio", round(a14.mean(), 3), "| spread precio", S.mean())
for d in (1, -1):
    idx = np.nonzero(rint == d)[0]; idx = idx[idx < len(tt) - 600]
    for retraso in (0, 1, 2):
        for mult_spr in (1, 2):
            e0 = tt[idx] + 60 * (1 + retraso)
            je, js, pe, ps, spr = simular2(T, O, H, L, S * mult_spr, e0, e0 + 60, np.full(len(idx), d, np.int64), np.zeros(len(idx)),
                                           2 * a14[idx], 2 * a14[idx], tt[idx + 500], 0.0, un, False)
            ok = je >= 0
            # una a la vez
            keep = []; libre = -1
            for r in np.argsort(je):
                if ok[r] and je[r] >= libre: keep.append(r); libre = js[r]
            keep = np.array(keep)
            neto = (ps[keep] - pe[keep]) * d * un - spr[keep]
            mes = pd.to_datetime(T[je[keep]], unit="s").to_period("M")
            pm = pd.Series(neto, index=mes).groupby(level=0).sum()
            print(f"{'compra' if d==1 else 'venta '} retraso {retraso} min, spread x{mult_spr}: ops {len(keep)}, aciertos {100*(neto>0).mean():.1f}%, "
                  f"USD/op {neto.mean():+.4f}, total {neto.sum():+.1f}, meses + {int((pm>0).sum())}/{len(pm)}, "
                  f"SL medio USD {(2*a14[idx]*un).mean():.3f}")

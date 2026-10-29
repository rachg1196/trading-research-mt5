import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "src")
import motor as mt
from smc_nb import motor, simular2, atr_sma
SIM = sys.argv[1]
sp = json.load(open("config/specs_sint2.json"))[SIM]
m1 = mt.cargar_m1(f"datos/sinteticos/{SIM}_M1.csv.gz", "2025-01-01", "2026-10-30")
un = sp["valor_1pct_lote_min"] / (0.01 * sp["ask"]); punto = sp["point"]
T = m1.time.to_numpy(np.int64); O = m1.open.to_numpy(float); H = m1.high.to_numpy(float); L = m1.low.to_numpy(float)
S = m1.spread.to_numpy(float) * punto; C = m1.close.to_numpy(float)
a14 = atr_sma(H, L, C, 14); rint = motor(O, H, L, C)[0]
out = []
for d in (1, -1):
    idx = np.nonzero(rint == d)[0]; idx = idx[idx < len(T) - 600]
    e0 = T[idx] + 60
    je, js, pe, ps, spr = simular2(T, O, H, L, S, e0, e0 + 60, np.full(len(idx), d, np.int64), np.zeros(len(idx)),
                                   2 * a14[idx], 2 * a14[idx], T[idx + 500], 0.0, un, False)
    keep = []; libre = -1
    for r in np.argsort(je):
        if je[r] >= 0 and je[r] >= libre: keep.append(r); libre = js[r]
    k = np.array(keep)
    sl = pe[k] - d * 2 * a14[idx[k]]
    perdio = (ps[k] - pe[k]) * d < 0
    ps2 = ps[k].copy()
    peor = np.where(d == 1, L[js[k]], H[js[k]])          # peor precio del minuto en que salto el SL
    ps2[perdio] = peor[perdio]
    n1 = (ps[k] - pe[k]) * d * un - spr[k]; n2 = (ps2 - pe[k]) * d * un - spr[k]
    salto = ((np.where(d == 1, sl - L[js[k]], H[js[k]] - sl))[perdio] / punto)
    out.append(f"{SIM} {'compra' if d==1 else 'venta '}: normal {n1.mean():+.4f} | peor caso SL {n2.mean():+.4f} | "
               f"perdedoras {perdio.mean()*100:.0f}% | deslizamiento medio si salta {np.mean(salto):.0f} pts (mediana {np.median(salto):.0f})")
print("\n".join(out))

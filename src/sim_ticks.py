import sys, numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, "src")
from smc_nb import motor, atr_sma
SIM = sys.argv[1]; UN = 0.1   # lote 0,10, contrato 1
tk = pd.read_csv(f"datos/ticks/{SIM}_ticks.csv.gz")
tk = tk[(tk.bid > 0) & (tk.ask > 0)].sort_values("time_msc").reset_index(drop=True)
ts = (tk.time_msc // 1000).to_numpy(np.int64); bid = tk.bid.to_numpy(float); ask = tk.ask.to_numpy(float)
dt = pd.to_datetime(tk.time_msc, unit="ms")
bars = tk.set_index(dt).bid.resample("1min").ohlc().dropna()
o, h, l, c = (bars[x].to_numpy(float) for x in ["open", "high", "low", "close"])
bt = bars.index.values.astype("datetime64[s]").astype(np.int64)
a14 = atr_sma(h, l, c, 14); rint = motor(o, h, l, c)[0]

@njit(cache=True)
def sim(ts, bid, ask, t_ent, d, dist, t_max):
    n = len(t_ent); res = np.zeros((n, 6)); k0 = 0
    for r in range(n):
        while k0 < len(ts) and ts[k0] < t_ent[r]: k0 += 1
        if k0 >= len(ts) - 1: res[r, 0] = -1; continue
        pe = ask[k0] if d[r] == 1 else bid[k0]
        sl = pe - d[r] * dist[r]; tp = pe + d[r] * dist[r]
        ps = 0.0; motivo = 0; k = k0; kfin = k0
        while k < len(ts):
            px = bid[k] if d[r] == 1 else ask[k]          # precio de cierre de la posicion
            if (d[r] == 1 and px <= sl) or (d[r] == -1 and px >= sl): ps = px; motivo = 1; kfin = k; break
            if (d[r] == 1 and px >= tp) or (d[r] == -1 and px <= tp): ps = px; motivo = 2; kfin = k; break
            if ts[k] >= t_max[r]: ps = px; motivo = 3; kfin = k; break
            k += 1
        if motivo == 0: res[r, 0] = -1; continue
        res[r, 0] = 1; res[r, 1] = pe; res[r, 2] = ps; res[r, 3] = motivo
        res[r, 4] = ts[kfin]; res[r, 5] = (ps - sl) * d[r]       # >0 si el SL se lleno peor que el nivel
    return res

for d in (1, -1):
    idx = np.nonzero(rint == d)[0]; idx = idx[idx < len(bt) - 600]
    t_ent = bt[idx] + 60
    out = sim(ts, bid, ask, t_ent, np.full(len(idx), d, np.int64), 2 * a14[idx], bt[idx] + 60 + 500 * 60)
    ok = out[:, 0] > 0
    # una a la vez
    keep = []; libre = -1
    for r in np.nonzero(ok)[0]:
        if t_ent[r] >= libre: keep.append(r); libre = out[r, 4]
    k = np.array(keep)
    pe, ps, mot = out[k, 1], out[k, 2], out[k, 3]
    neto = (ps - pe) * d * UN                     # el spread ya esta en bid/ask reales
    sl_m = mot == 1
    desl = -out[k, 5][sl_m] if d == 1 else out[k, 5][sl_m]
    desl = np.abs(out[k, 5][sl_m])
    print(f"{SIM} {'compra' if d==1 else 'venta '}: ops {len(k)} | aciertos {100*(neto>0).mean():.1f}% | USD/op {neto.mean():+.4f} | "
          f"total {neto.sum():+.1f} | SL {100*sl_m.mean():.0f}% (deslizamiento medio en SL {np.mean(desl)/0.01:.0f} pts, mediana {np.median(desl)/0.01:.0f}) | "
          f"spread medio {np.mean(ask-bid)/0.01:.0f} pts")

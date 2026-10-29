"""Verificacion con ticks de la regla FTS Spike ruptura (BreakX 600 M5). Plan: docs/PLAN_FTS_TICKS.md
A = metodo original (velas M1: SL al peor precio de la vela, entrada en la linea o en la apertura)
B = tick a tick (entrada en el primer tick que cruza la linea; SL/TP en el primer tick que los cruza)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/analisis")
from fts import senales
TP, SL, HOLD = 50.0, 110.0, 2*24*3600          # en precio (5.000 / 11.000 puntos, punto 0,01)
fl = pd.read_csv(sys.argv[1]); fl = fl[fl.b0 > 0]
m1 = pd.read_csv("/home/claude/datos_sint2/BreakX600_M1.csv.gz")
tk = pd.read_csv("/home/claude/ticks/BreakX600_ticks.csv.gz"); tk = tk[(tk.bid > 0) & (tk.ask > 0)].sort_values("time_msc")
ts = (tk.time_msc // 1000).to_numpy(np.int64); bid = tk.bid.to_numpy(float); ask = tk.ask.to_numpy(float)
t0, t1 = ts[0] + 3600, ts[-1] - HOLD            # ventana con ticks (dejando 48 h para cerrar)
m5 = m1.assign(g=m1.time // 300 * 300).groupby("g").agg(open=("open","first"), high=("high","max"), low=("low","min")).reset_index().rename(columns={"g":"time"})
sig = [(int(m5.time[j]), d, lv) for j, d, lv in senales(m5, fl) if t0 <= m5.time[j] < t1]
T1 = m1.time.to_numpy(); O = m1.open.to_numpy(float); H = m1.high.to_numpy(float); L = m1.low.to_numpy(float); SP = m1.spread.to_numpy(float) / 100
def sim_velas(t, d, lv):
    s = np.searchsorted(T1, t)
    for i in range(s, s + 5):
        if (d == 1 and H[i] >= lv) or (d == -1 and L[i] <= lv): break
    else: return None
    e = (max(lv, O[i]) + SP[i]) if d == 1 else min(lv, O[i])
    end = np.searchsorted(T1, T1[i] + HOLD)
    for k in range(i, end):
        if d == 1: adv, fav = e - L[k], (H[k] - e if k > i else -1e9)
        else: adv, fav = H[k] + SP[k] - e, (e - L[k] - SP[k] if k > i else -1e9)
        if adv >= SL: return -max(adv, SL)
        if fav >= TP: return TP
    k = end - 1; return (O[k] - e) if d == 1 else (e - O[k] - SP[k])
def sim_ticks(t, d, lv):
    a = np.searchsorted(ts, t); b = np.searchsorted(ts, t + 300)
    w = np.nonzero(bid[a:b] >= lv if d == 1 else bid[a:b] <= lv)[0]
    if len(w) == 0: return None, 0
    k = a + w[0]; e = ask[k] if d == 1 else bid[k]
    desliz = (e - lv) if d == 1 else (lv - e)     # cuanto peor que la linea se entro (incluye spread en compra)
    px = bid if d == 1 else ask; end = np.searchsorted(ts, ts[k] + HOLD)
    r = (px[k+1:end] - e) * d
    i_sl = np.argmax(r <= -SL) if (r <= -SL).any() else 10**12; i_tp = np.argmax(r >= TP) if (r >= TP).any() else 10**12
    if i_sl < i_tp: return r[i_sl], desliz
    if i_tp < 10**12: return r[i_tp], desliz
    return r[-1], desliz
A, B, D = [], [], []
for t, d, lv in sig:
    a = sim_velas(t, d, lv); bb, ds = sim_ticks(t, d, lv)
    if a is None or bb is None: continue
    A.append(a); B.append(bb); D.append(ds)
A, B, D = (np.array(x) * 100 for x in (A, B, D))   # a puntos
print(f"Ventana: {pd.to_datetime(t0,unit='s')} -> {pd.to_datetime(t1,unit='s')} | señales {len(sig)} | operaciones comparables {len(A)}")
for n, x in (("A velas M1", A), ("B ticks   ", B)):
    print(f"{n}: aciertos {np.mean(x>0)*100:5.1f}%  pts/op {x.mean():+8.1f}  total {x.sum():+10.0f} pts (= {x.sum()*0.001:+.2f} USD lote 0,1)  peor {x.min():.0f}")
print(f"Diferencia B-A por operacion: {(B-A).mean():+.1f} pts | entrada peor que la linea (mediana) {np.median(D):.0f} pts, p90 {np.percentile(D,90):.0f}")
perd = B < 0; print(f"Perdidas con ticks: media {B[perd].mean():.0f} pts (nivel teorico -11.000)")
ok = B.mean() > 0 and (B - A).mean() > -150
print("DECISION:", "SIGUE EN PIE -> probar en demo" if ok else "NO SE SOSTIENE con ticks")

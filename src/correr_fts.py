import sys, os, json, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor, wm, fts
from scipy.stats import norm
SIM, INI, FIN = sys.argv[1:4]
D = "datos/completo/"
F = "datos/fts/"
sp = json.load(open("config/specs_todos.json"))[SIM]
ini, fin = pd.Timestamp(INI), pd.Timestamp(FIN); corte = ini + 0.75 * (fin - ini)
m1 = motor.cargar_m1(D + f"{SIM}_M1.csv.gz", ini, corte)
punto = sp["point"]; unidades = sp["valor_1pct_lote_min"] / (0.01 * sp["ask"])
ult = m1[m1.dt >= corte - pd.Timedelta(days=365)]
_c = pd.read_csv(D + f"{SIM}_M1.csv.gz", usecols=["open", "spread"]).tail(7000)
spct = max(float((ult.spread * punto / ult.open).median()), float((_c.spread * punto / _c.open).median()))
costes = dict(punto=punto, unidades=unidades, spread_pct=spct, swap_modo=sp["swap_mode"], swap_long=sp["swap_long"], swap_short=sp["swap_short"], swap_triple=sp["swap_rollover3days"])
T = m1.time.to_numpy(); O = m1.open.to_numpy(); H = m1.high.to_numpy(); L = m1.low.to_numpy(); S = m1.spread.to_numpy() * punto
anio = m1.dt.dt.year.to_numpy(); HOLD = 2 * 1440

def trade(j, d, pe, tpd, sld):
    b = min(j + HOLD, len(T) - 1)
    hh = H[j:b]; ll = L[j:b]
    tp = pe + d * tpd; sl = pe - d * sld
    if d == 1: hs = ll <= sl; ht = hh >= tp
    else: hs = hh >= sl; ht = ll <= tp
    ks = np.argmax(hs) if hs.any() else 10**9; kt = np.argmax(ht) if ht.any() else 10**9
    if ks == 10**9 and kt == 10**9: ps, k = O[b], b
    elif ks <= kt: ps = sl if ks == 0 else (min(sl, O[j + ks]) if d == 1 else max(sl, O[j + ks])); k = j + ks
    else: ps, k = tp, j + kt
    spr = max(S[j], spct * pe) * unidades
    return (ps - pe) * d * unidades - spr, spr, k

filas = []
for tf in ["M5", "M1", "M15"]:
    fp = F + f"fts_{SIM}_{tf}.csv"
    fl = pd.read_csv(fp)
    tfdf = motor.armar_tf(m1, tf); per = motor.MIN[tf] * 60
    if fl.time.max() < tfdf.time.iloc[-1] - 30 * 86400 or fl.time.min() > tfdf.time.iloc[0] + 30 * 86400:
        print(tf, "flechas incompletas, se salta"); continue
    t0 = time.time()
    sen = fts.senales(tfdf, fl)
    tt = tfdf.time.to_numpy()
    c = tfdf.close.to_numpy(float); h = tfdf.high.to_numpy(float); l = tfdf.low.to_numpy(float)
    pc = np.r_[c[0], c[:-1]]; atr = pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).ewm(alpha=1/14, adjust=False).mean().to_numpy()
    for var in ["A: TP 1 USD neto + spread, SL 2.2x", "B: TP 2 ATR, SL 4.4 ATR"]:
        res = []
        for jb, d, lv in sen:
            a = np.searchsorted(T, tt[jb]); b = np.searchsorted(T, tt[jb] + per)
            j = -1
            for q in range(a, min(b, len(T) - 1)):
                if (d == 1 and H[q] >= lv) or (d == -1 and L[q] <= lv):
                    j = q; pe = max(lv, O[q]) if d == 1 else min(lv, O[q]); break
            if j < 0: continue
            if var.startswith("A"):
                tpd = (1 + max(S[j], spct * pe) * unidades) / unidades
            else:
                tpd = 2 * atr[jb - 1]
            sld = 2.2 * tpd
            neto, spr, k = trade(j, d, pe, tpd, sld)
            sw = wm.costes_swap(np.array([T[j]]), np.array([T[k]]), np.array([pe]), np.array([d]), costes)[0]
            res.append((j, d, neto + sw, spr, tpd, sld, k))
        R = pd.DataFrame(res, columns=["j", "d", "neto", "spr", "tpd", "sld", "k"])
        for d, nom in [(1, "compras"), (-1, "ventas")]:
            r = R[R.d == d].sort_values("j")
            keep = []; libre = -1
            for idx_, row in r.iterrows():
                if row.j >= libre: keep.append(idx_); libre = row.k
            r = r.loc[keep]
            base = dict(simbolo=SIM, tf=tf, variante=var, direccion=nom)
            if len(r) < 2: filas.append(dict(base, ops=len(r))); continue
            neto = r.neto.to_numpy(); med = neto.mean()
            rng = np.random.default_rng(5); M = 3000; pares = r[["tpd", "sld"]].to_numpy()
            js = rng.integers(0, len(T) - HOLD - 2, M); pi = rng.integers(0, len(pares), M)
            az = np.array([trade(jj, d, O[jj], *pares[q])[0] for jj, q in zip(js, pi)])
            se = np.sqrt(neto.var() / len(neto) + az.var() / M)
            p = float(norm.sf((med - az.mean()) / se)) if se > 0 else 1.0
            medias = az
            an = pd.Series(neto, index=anio[r.j.astype(int)]).groupby(level=0).sum()
            r15 = neto - 0.5 * r.spr.to_numpy(); eq = np.cumsum(neto)
            filas.append(dict(base, ops=len(r), aciertos_pct=round(100 * (neto > 0).mean(), 1), usd_por_op=round(med, 4),
                usd_total=round(neto.sum(), 2), tp_usd=round((r.tpd * unidades).mean(), 3), sl_usd=round((r.sld * unidades).mean(), 3),
                peor_caida_usd=round(float((np.maximum.accumulate(eq) - eq).max()), 2), azar_media=round(float(medias.mean()), 4),
                p_normal=p, anios_positivos=f"{int((an > 0).sum())}/{len(an)}", anios_pos_frac=float((an > 0).mean()),
                usd_por_op_spread15=round(r15.mean(), 4)))
    print(tf, len(sen), "senales", f"{time.time()-t0:.0f}s", flush=True)
tab = pd.DataFrame(filas); tab.to_csv(f"resultados/fts_{SIM}.csv", index=False)
print(tab.drop(columns=["simbolo"]).to_string())

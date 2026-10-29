# -*- coding: utf-8 -*-
"""Prueba de las estrategias de los videos en PainX (~Crash) y GainX (~Boom) de Weltrade.
C&B: solo a favor de la deriva (PainX compra / GainX venta), TP = SL = D (1:1, como '20.000 pts arriba/abajo').
     Entradas: (a) al azar, (b) justo despues de un spike, (c) tras 10 min sin spike.  (las 3 deberian dar igual)
FIBO 61.8: tras cada spike, medir el spike (L->H en GainX / H->L en PainX); cuando la deriva devuelve el 61.8%,
     entrar a favor del spike (GainX compra / PainX venta) con SL = s y TP = 2s (como el video: SL 10-15, TP 20-30).
Simulacion en velas M1; si un spike cruza el SL, se llena en el extremo de la vela (realista). Spread real del mercado."""
import sys, json, numpy as np, pandas as pd
D = sys.argv[1]
SPREAD = {"400": .78, "600": .80, "800": .63, "999": .96, "1200": .45}   # precio (puntos/100)
rng = np.random.default_rng(5)

def sim(o, h, l, c, salto, e, d, tp, sl, maxb=600):
    n = len(o); E = o[e]; fin = min(n, e + maxb)
    hh, ll = h[e:fin], l[e:fin]
    if d == 1: t = hh >= E + tp; s = ll <= E - sl
    else:      t = ll <= E - tp; s = hh >= E + sl
    it = np.argmax(t) if t.any() else 10**9; is_ = np.argmax(s) if s.any() else 10**9
    if is_ < 10**9 and is_ <= it:
        k = e + is_
        if salto[k]: return (l[k] - E) if d == 1 else (E - h[k])
        return -sl
    if it < 10**9: return tp
    return d * (c[fin - 1] - E)

out = []
for fam in ["PainX", "GainX"]:
    for v in ["400", "600", "800", "999", "1200"]:
        s = f"{fam}_{v}"; sp = SPREAD[v]
        m = pd.read_parquet(f"{D}/{s}/M1.parquet"); m = m[m.tick_volume > 0].reset_index(drop=True)
        o, h, l, c = [m[k].to_numpy() for k in ["open", "high", "low", "close"]]
        r = h - l; salto = r > 4 * np.median(r); idx = np.where(salto)[0]; n = len(o)
        drift = np.median(np.abs(c - o)[~salto])
        dir_deriva = 1 if fam == "PainX" else -1
        # ---- C&B: TP = SL = D, D en "minutos de deriva"
        for kmin in [2, 5, 7, 10, 20]:
            Dd = kmin * drift
            for modo in ["azar", "tras_spike", "10min_sin_spike"]:
                if modo == "azar": E = rng.integers(100, n - 700, 4000)
                elif modo == "tras_spike": E = idx[(idx > 100) & (idx < n - 700)] + 1
                else:
                    gap = np.diff(idx); ok = gap > 10   # sin spike en las 10 velas previas; la vela de entrada puede tener spike
                    E = idx[:-1][ok] + 11; E = E[(E > 100) & (E < n - 700)]
                if len(E) > 4000: E = rng.choice(E, 4000, replace=False)
                p = np.array([sim(o, h, l, c, salto, e, dir_deriva, Dd, Dd) for e in E]) - sp
                out.append(dict(mercado=s, estrategia="C&B 1:1", parametro=f"D={kmin} min de deriva ({Dd:.1f})", entrada=modo,
                                ops=len(p), acierto=(p > 0).mean(), neto_pts=p.mean() * 100,
                                z=p.mean() / (p.std() / np.sqrt(len(p)))))
        # ---- FIBO 61.8 contra la deriva (esperando el spike)
        for s_min in [3, 5, 8]:
            sl = s_min * drift; tp = 2 * sl
            P = []
            for a in idx[(idx > 5) & (idx < n - 700)]:
                if dir_deriva == -1:        # GainX: spike al alza L->H
                    L = l[a]; H = max(h[a], c[a]); lvl = H - 0.618 * (H - L)
                    seg = l[a + 1:a + 300]; hit = np.argmax(seg <= lvl) if (seg <= lvl).any() else -1
                else:                       # PainX: spike a la baja H->L
                    H = h[a]; L = min(l[a], c[a]); lvl = L + 0.618 * (H - L)
                    seg = h[a + 1:a + 300]; hit = np.argmax(seg >= lvl) if (seg >= lvl).any() else -1
                if hit < 0: continue
                e = a + 1 + hit + 1        # entra en la vela siguiente a tocar el 61.8
                if e >= n - 700: continue
                P.append(sim(o, h, l, c, salto, e, -dir_deriva, tp, sl) - sp)
            P = np.array(P)
            if len(P): out.append(dict(mercado=s, estrategia="Fibo 61.8 (SL s, TP 2s)", parametro=f"s={s_min} min de deriva ({sl:.1f})",
                                       entrada="toque 61.8", ops=len(P), acierto=(P > 0).mean(), neto_pts=P.mean() * 100,
                                       z=P.mean() / (P.std() / np.sqrt(len(P)))))
        print(s, "ok", flush=True)
r = pd.DataFrame(out); r.to_csv(sys.argv[2], index=False)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 300)
print(r.round(2).to_string(index=False))

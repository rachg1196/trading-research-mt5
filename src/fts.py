# -*- coding: utf-8 -*-
"""Regla validada en BreakX (proyecto anterior): RUPTURA de la linea de FTS SPIKE.
Flechas usables solo 10 velas despues (ya no repintan). Linea de arriba = 2 ultimas flechas rojas (debe ser
bajista); linea de abajo = 2 ultimas azules (debe ser alcista). Toca la de arriba -> COMPRA; la de abajo -> VENTA.
Cada linea se usa una vez."""
import numpy as np, pandas as pd

def senales(tfdf, flechas, espera=10):
    t = tfdf.time.to_numpy(); o = tfdf.open.to_numpy(float); h = tfdf.high.to_numpy(float); l = tfdf.low.to_numpy(float)
    idx = {v: i for i, v in enumerate(t)}
    fl = [(idx[a], p, int(c)) for a, p, c in zip(flechas.time, flechas.b0, flechas.b1) if a in idx]
    fl.sort()
    out = []; usadas = set(); di = 0; vistas = []
    for k in range(200, len(t) - 1):
        while di < len(fl) and fl[di][0] <= k - espera:
            vistas.append(fl[di]); di += 1
        rec = vistas[-6:]
        for col in (1, 0):
            pts = [x for x in rec if x[2] == col][-2:]
            if len(pts) < 2 or pts[0][0] == pts[1][0]: continue
            (i1, p1, _), (i2, p2, _) = pts; m = (p2 - p1) / (i2 - i1)
            if (col == 1 and m >= 0) or (col == 0 and m <= 0): continue
            if (col, i2) in usadas: continue
            j = k + 1; lv = p2 + m * (j - i2)
            if (col == 1 and h[j] >= lv and o[j] < lv) or (col == 0 and l[j] <= lv and o[j] > lv):
                usadas.add((col, i2)); out.append((j, 1 if col == 1 else -1, lv))
    return out

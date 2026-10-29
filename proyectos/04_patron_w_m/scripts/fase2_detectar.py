# -*- coding: utf-8 -*-
"""
FASE 2 - Corre el detector en todos los mercados y temporalidades (solo datos de desarrollo)
y genera imagenes de ejemplos elegidos AL AZAR (no por resultado).
Uso: python fase2_detectar.py <carpeta_datos_historico> <carpeta_salida>
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector
import graficos

DATOS = sys.argv[1]
SALIDA = sys.argv[2]
INICIO_VIVO = pd.Timestamp("2025-06-16")  # antes: historia con volumen 0 y spread 0 (pre-lanzamiento)
SIMBOLOS = ["BreakX_600", "TrendX_600", "SwitchX_600"]
TFS = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30",
       "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1", "W1", "MN1"]

os.makedirs(os.path.join(SALIDA, "imagenes"), exist_ok=True)
os.makedirs(os.path.join(SALIDA, "resultados"), exist_ok=True)

todos, conteo = [], []
for s in SIMBOLOS:
    for tf in TFS:
        df = pd.read_parquet(os.path.join(DATOS, s, f"{tf}.parquet"))
        df = df[df["time"] >= INICIO_VIVO].reset_index(drop=True)
        dias = max(1, (df["time"].iloc[-1] - df["time"].iloc[0]).days) if len(df) else 1
        r = detector.detectar(df) if len(df) > 50 else pd.DataFrame()
        n = len(r)
        fila = dict(simbolo=s.replace("_", " "), tf=tf, velas=len(df), dias=dias, patrones=n,
                    por_dia=round(n / dias, 2))
        if n:
            fila.update(W=int((r.tipo == "W").sum()), M=int((r.tipo == "M").sum()),
                        triples=int((r.toques == 3).sum()),
                        alto=int((r.variante == "alto").sum()), igual=int((r.variante == "igual").sum()),
                        barrida=int((r.variante == "barrida").sum()))
            r.insert(0, "tf", tf); r.insert(0, "simbolo", s.replace("_", " "))
            todos.append(r)
        conteo.append(fila)
        print(f"{s:<12} {tf:<4} patrones={n:>6}  por dia={n / dias:6.2f}")

pat = pd.concat(todos, ignore_index=True)
pat.to_csv(os.path.join(SALIDA, "resultados", "fase2_patrones.csv"), index=False)
cnt = pd.DataFrame(conteo).fillna(0)
cnt.to_csv(os.path.join(SALIDA, "resultados", "fase2_conteo.csv"), index=False)

# ---- ejemplos al azar, repartidos entre mercados / temporalidades / variantes ----
rng = np.random.default_rng(20261020)
plan = [
    ("BreakX_600", "M5", "W", "alto", 2), ("BreakX_600", "M1", "M", "igual", 2),
    ("BreakX_600", "M15", "W", "barrida", 2), ("BreakX_600", "M5", "M", "alto", 3),
    ("TrendX_600", "M5", "M", "barrida", 2), ("TrendX_600", "M3", "W", "igual", 2),
    ("TrendX_600", "H1", "W", "alto", 2), ("TrendX_600", "M15", "M", "igual", 3),
    ("SwitchX_600", "M5", "W", "igual", 2), ("SwitchX_600", "M2", "M", "alto", 2),
    ("SwitchX_600", "M30", "W", "barrida", 2), ("SwitchX_600", "M10", "W", "alto", 3),
]
nombres_var = {"alto": "2do extremo se queda corto", "igual": "2do extremo al mismo nivel",
               "barrida": "2do extremo barre al 1ro"}
for k, (s, tf, tipo, var, toq) in enumerate(plan, 1):
    df = pd.read_parquet(os.path.join(DATOS, s, f"{tf}.parquet"))
    df = df[df["time"] >= INICIO_VIVO].reset_index(drop=True)
    r = pat[(pat.simbolo == s.replace("_", " ")) & (pat.tf == tf) & (pat.tipo == tipo)
            & (pat.variante == var) & (pat.toques == toq)]
    if r.empty:
        continue
    p = r.iloc[rng.integers(len(r))]
    tit = (f"Ejemplo {k:02d}  |  {s.replace('_', ' ')}  {tf}  |  {tipo} {'triple' if toq == 3 else 'doble'}"
           f"  |  {nombres_var[var]}  |  senal {pd.Timestamp(p.t_senal):%d-%b-%Y %H:%M} (hora servidor)")
    graficos.dibujar(df, p, tit, os.path.join(SALIDA, "imagenes", f"ejemplo_{k:02d}_{s}_{tf}_{tipo}_{var}.png"))
print("listo")

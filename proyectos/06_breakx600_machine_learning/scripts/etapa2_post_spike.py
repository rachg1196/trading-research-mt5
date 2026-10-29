"""
PROYECTO BREAKX 600 — ETAPA 2
Análisis de secuencias post-spike:
  ¿Qué ocurre después de una vela con rango >= umbral?
  ¿Alcanza TP antes que SL? ¿En cuántas velas?
  ¿Hay diferencia por dirección, horario, cuerpo vs mechas?

Metodología: simulación vela a vela sin filtración de futuro.
Entrada: al cierre de la vela spike.
TP/SL: medidos usando high/low de las velas siguientes.
No se usan ticks aquí (eso es validación posterior).

Calibración:
  POINT = 0.01
  TP = 5000 pts = 50.00 en precio
  SL = 5000 pts = 50.00 en precio
  Spread = 130 pts = 1.30 en precio (se aplica a la entrada)
"""

import polars as pl
import numpy as np
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT  = BASE / "output"
POINT = 0.01

# ─────────────────────────────────────────────────────────
# PARÁMETROS
# ─────────────────────────────────────────────────────────
SPIKE_UMBRALES = [3000, 3500, 4000, 5000]   # rango vela spike (pts)
TP_PTS  = 5000    # take profit en puntos
SL_PTS  = 5000    # stop loss en puntos
MAX_VEL = 20      # máximo de velas a mirar hacia adelante (horizonte)
SPREAD  = 130     # puntos de spread (se resta al TP efectivo, suma al SL efectivo)

# ─────────────────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────────────────
print("=" * 65)
print("ETAPA 2 — ANÁLISIS POST-SPIKE")
print("=" * 65)

m5 = pl.read_parquet(OUT / "m5_limpio.parquet").sort("dt")
print(f"Velas cargadas: {len(m5):,}")

# Convertir a numpy para simulación rápida vela a vela
dt_arr     = m5["dt"].to_numpy()
open_arr   = m5["open"].to_numpy()
high_arr   = m5["high"].to_numpy()
low_arr    = m5["low"].to_numpy()
close_arr  = m5["close"].to_numpy()
rango_arr  = m5["rango_pts"].to_numpy()
dir_arr    = m5["direccion"].to_numpy()
cuerpo_arr = m5["cuerpo_pts"].to_numpy()

N = len(m5)
TP_PRICE  = TP_PTS  * POINT
SL_PRICE  = SL_PTS  * POINT
SP_PRICE  = SPREAD  * POINT

# ─────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL: simular entrada al cierre del spike
# ─────────────────────────────────────────────────────────
def simular_post_spike(spike_umbral: int, tp_pts: int, sl_pts: int,
                        max_velas: int, spread_pts: int) -> pl.DataFrame:
    """
    Para cada vela spike (rango >= umbral):
      - Entrar en la DIRECCIÓN de la vela (close > open → BUY, close < open → SELL)
      - Precio de entrada: close + spread/2 (BUY) o close - spread/2 (SELL)
      - TP y SL desde precio de entrada
      - Simular velas siguientes: el primero en tocarse gana/pierde
    Retorna DataFrame con resultados individuales.
    """
    tp_p   = tp_pts  * POINT
    sl_p   = sl_pts  * POINT
    sp_p   = spread_pts * POINT

    resultados = []
    spike_indices = np.where(rango_arr >= spike_umbral)[0]

    for idx in spike_indices:
        if idx + max_velas >= N:
            continue  # no hay suficientes velas futuras
        
        direccion = dir_arr[idx]
        if direccion == 0:
            continue  # doji, sin dirección clara

        entry_close = close_arr[idx]
        hora        = dt_arr[idx]
        hora_h      = (int(str(hora)[:13].split('T')[1][:2]) if 'T' in str(hora) 
                       else int(str(hora)[11:13]))  # hora 0-23

        if direccion == 1:  # BUY
            entry   = entry_close + sp_p / 2  # pagamos spread al entrar
            tp_lvl  = entry + tp_p
            sl_lvl  = entry - sl_p
        else:  # SELL
            entry   = entry_close - sp_p / 2
            tp_lvl  = entry - tp_p
            sl_lvl  = entry + sl_p

        resultado = None
        velas_hasta = None
        max_favor   = 0.0
        max_contra  = 0.0

        for j in range(1, max_velas + 1):
            k = idx + j
            if k >= N:
                break
            h = high_arr[k]
            l = low_arr[k]

            if direccion == 1:  # BUY
                excursion_favor  = (h - entry) / POINT
                excursion_contra = (entry - l) / POINT
                max_favor  = max(max_favor,  excursion_favor)
                max_contra = max(max_contra, excursion_contra)
                tp_hit = h >= tp_lvl
                sl_hit = l <= sl_lvl
            else:  # SELL
                excursion_favor  = (entry - l) / POINT
                excursion_contra = (h - entry) / POINT
                max_favor  = max(max_favor,  excursion_favor)
                max_contra = max(max_contra, excursion_contra)
                tp_hit = l <= tp_lvl
                sl_hit = h >= sl_lvl

            if tp_hit and sl_hit:
                # Ambos tocados en la misma vela → conservador: SL gana
                resultado   = "SL"
                velas_hasta = j
                break
            elif tp_hit:
                resultado   = "TP"
                velas_hasta = j
                break
            elif sl_hit:
                resultado   = "SL"
                velas_hasta = j
                break

        if resultado is None:
            resultado   = "TIMEOUT"
            velas_hasta = max_velas

        resultados.append({
            "dt":           hora,
            "direccion":    int(direccion),
            "rango_pts":    int(rango_arr[idx]),
            "cuerpo_pts":   int(cuerpo_arr[idx]),
            "entry_price":  round(entry, 2),
            "resultado":    resultado,
            "velas_hasta":  int(velas_hasta),
            "max_favor_pts":  round(max_favor),
            "max_contra_pts": round(max_contra),
        })

    return pl.DataFrame(resultados)


# ─────────────────────────────────────────────────────────
# EJECUTAR PARA DISTINTOS UMBRALES
# ─────────────────────────────────────────────────────────
print(f"\nParámetros: TP={TP_PTS}pts | SL={SL_PTS}pts | Spread={SPREAD}pts | Horizonte={MAX_VEL} velas\n")
print(f"{'Umbral':>8} {'#Señales':>10} {'#TP':>8} {'#SL':>8} {'#TO':>8} {'%TP':>8} {'EM_bruta':>10} {'Velas_med':>10}")
print("-" * 75)

resultados_por_umbral = {}
for u in SPIKE_UMBRALES:
    df = simular_post_spike(u, TP_PTS, SL_PTS, MAX_VEL, SPREAD)
    n   = len(df)
    ntp = (df["resultado"] == "TP").sum()
    nsl = (df["resultado"] == "SL").sum()
    nto = (df["resultado"] == "TIMEOUT").sum()
    ptp = 100 * ntp / n if n > 0 else 0
    # Expectativa matemática bruta (TP=+1 ratio, SL=-1 ratio, TO=0 por simplicidad)
    em  = (ntp * TP_PTS - nsl * SL_PTS) / n if n > 0 else 0
    vel_med = df.filter(pl.col("resultado") != "TIMEOUT")["velas_hasta"].mean()
    resultados_por_umbral[u] = df
    print(f"  {u:>6,}  {n:>10,}  {ntp:>8,}  {nsl:>8,}  {nto:>8,}  {ptp:>7.1f}%  {em:>10,.0f}  {vel_med:>10.2f}")

# ─────────────────────────────────────────────────────────
# ANÁLISIS DETALLADO: UMBRAL 3500 PTS
# ─────────────────────────────────────────────────────────
U = 3500
df3500 = resultados_por_umbral[U]
print(f"\n{'='*65}")
print(f"ANÁLISIS DETALLADO — Spike umbral {U:,} pts")
print(f"{'='*65}")

print(f"\nTotal señales: {len(df3500):,}")

# -- Por dirección --
print("\n--- Resultados por DIRECCIÓN ---")
for d, dname in [(1, "BUY"), (-1, "SELL")]:
    sub = df3500.filter(pl.col("direccion") == d)
    n   = len(sub)
    ntp = (sub["resultado"] == "TP").sum()
    nsl = (sub["resultado"] == "SL").sum()
    nto = (sub["resultado"] == "TIMEOUT").sum()
    ptp = 100 * ntp / n if n > 0 else 0
    em  = (ntp * TP_PTS - nsl * SL_PTS) / n if n > 0 else 0
    print(f"  {dname}: n={n:,} | TP={ntp:,} ({100*ntp/n:.1f}%) | SL={nsl:,} ({100*nsl/n:.1f}%) | TO={nto:,} | EM={em:,.0f} pts")

# -- Por tamaño de cuerpo (relación cuerpo/rango) --
print("\n--- Resultados por RELACIÓN CUERPO/RANGO ---")
df3500 = df3500.with_columns(
    (pl.col("cuerpo_pts").cast(pl.Float64) / pl.col("rango_pts").cast(pl.Float64)).alias("ratio_cuerpo")
)
bins = [(0.0, 0.5, "cuerpo<50%"), (0.5, 0.75, "cuerpo 50-75%"), (0.75, 0.9, "cuerpo 75-90%"), (0.9, 1.01, "cuerpo>90%")]
for lo, hi, label in bins:
    sub = df3500.filter((pl.col("ratio_cuerpo") >= lo) & (pl.col("ratio_cuerpo") < hi))
    n   = len(sub)
    if n == 0:
        continue
    ntp = (sub["resultado"] == "TP").sum()
    nsl = (sub["resultado"] == "SL").sum()
    nto = (sub["resultado"] == "TIMEOUT").sum()
    ptp = 100 * ntp / n
    em  = (ntp * TP_PTS - nsl * SL_PTS) / n
    print(f"  {label:>16}: n={n:>6,} | TP={ptp:>5.1f}% | SL={100*nsl/n:>5.1f}% | TO={100*nto/n:>5.1f}% | EM={em:>8,.0f} pts")

# -- Por hora del día (GMT+3) --
print("\n--- Resultados por HORA DEL DÍA (GMT+3) ---")
# dt is numpy datetime64 stored as object; extract hour via pandas
import pandas as pd
df3500_h = df3500.with_columns(
    pl.Series("hora", pd.DatetimeIndex(df3500["dt"].to_list()).hour.tolist(), dtype=pl.Int32)
)
hora_res = (
    df3500_h.group_by("hora")
    .agg([
        pl.len().alias("n"),
        (pl.col("resultado") == "TP").sum().alias("ntp"),
        (pl.col("resultado") == "SL").sum().alias("nsl"),
        (pl.col("resultado") == "TIMEOUT").sum().alias("nto"),
    ])
    .sort("hora")
    .with_columns([
        (100 * pl.col("ntp") / pl.col("n")).alias("pct_tp"),
        ((pl.col("ntp") * TP_PTS - pl.col("nsl") * SL_PTS) / pl.col("n")).alias("em"),
    ])
)
print(hora_res)

# -- Distribución de velas hasta resultado --
print("\n--- DISTRIBUCIÓN DE VELAS HASTA TP/SL (excluye TIMEOUT) ---")
df_hit = df3500.filter(pl.col("resultado") != "TIMEOUT")
velas_dist = (
    df_hit.group_by(["resultado", "velas_hasta"])
    .agg(pl.len().alias("n"))
    .sort(["resultado", "velas_hasta"])
)
# Acumulado hasta N velas
for res in ["TP", "SL"]:
    sub = df_hit.filter(pl.col("resultado") == res)
    total = len(sub)
    print(f"\n  {res} — {total:,} operaciones:")
    cumul = 0
    for v in [1, 2, 3, 4, 5, 7, 10, 15, 20]:
        n_v = (sub["velas_hasta"] <= v).sum()
        cumul = n_v
        print(f"    <= {v:>2} velas: {n_v:>6,} ({100*n_v/total:.1f}%)")

# -- Excursión máxima a favor antes de SL --
print("\n--- EXCURSIÓN MÁXIMA A FAVOR (en operaciones que terminan en SL) ---")
sl_ops = df3500.filter(pl.col("resultado") == "SL")
fav = sl_ops["max_favor_pts"].to_numpy()
for v in [1000, 2000, 3000, 4000, 5000]:
    n = (fav >= v).sum()
    print(f"  Alcanzó {v:>6,} pts a favor antes del SL: {n:,} ({100*n/len(sl_ops):.1f}%)")

# -- Por mes (in-sample vs separado) --
print("\n--- RESULTADOS POR MES ---")
df3500_mes = df3500.with_columns(
    pl.Series("mes", pd.DatetimeIndex(df3500["dt"].to_list()).strftime("%Y-%m").tolist(), dtype=pl.String)
)
mes_res = (
    df3500_mes.group_by("mes")
    .agg([
        pl.len().alias("n"),
        (pl.col("resultado") == "TP").sum().alias("ntp"),
        (pl.col("resultado") == "SL").sum().alias("nsl"),
    ])
    .sort("mes")
    .with_columns([
        (100 * pl.col("ntp") / pl.col("n")).alias("pct_tp"),
        ((pl.col("ntp") * TP_PTS - pl.col("nsl") * SL_PTS) / pl.col("n")).alias("em"),
    ])
)
print(f"{'Mes':>10} {'n':>7} {'TP%':>8} {'EM(pts)':>10}")
for row in mes_res.iter_rows(named=True):
    print(f"  {row['mes']}  {row['n']:>7,}  {row['pct_tp']:>7.1f}%  {row['em']:>10,.0f}")

# -- GUARDAR RESULTADOS --
print("\n--- GUARDANDO ---")
def fix_df(df):
    # Polars cannot cast Object dtype — convert via pandas
    pd_df = df.to_pandas()
    pd_df["dt"] = pd_df["dt"].astype(str)
    return pl.from_pandas(pd_df)

fix_df(df3500).write_parquet(OUT / "post_spike_3500.parquet")
for u in SPIKE_UMBRALES:
    fix_df(resultados_por_umbral[u]).write_parquet(OUT / f"post_spike_{u}.parquet")
print("  Archivos guardados en output/")

print("\n" + "=" * 65)
print("ETAPA 2 COMPLETADA")
print("=" * 65)

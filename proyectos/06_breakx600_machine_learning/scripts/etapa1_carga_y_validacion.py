"""
PROYECTO BREAKX 600 — ETAPA 1
Carga unificada M5, validación de calidad, estadísticas base y primera
exploración de spikes.

Librerías: Polars (Big Data), NumPy, SciPy
Zona horaria: GMT+3 (servidor MT5). Se conserva tal cual.
Unidades: 1 punto = 0.01 precio (symbol_point = 0.01)
"""

import polars as pl
import numpy as np
from pathlib import Path
import sys

# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
CSV_DIR = BASE / "CSV COMPLETOS"
OUT_DIR = BASE / "output"
OUT_DIR.mkdir(exist_ok=True)

POINT = 0.01  # symbol_point

# ─────────────────────────────────────────────
# 1. CARGA DE LOS 4 CSV M5
# ─────────────────────────────────────────────
print("=" * 60)
print("ETAPA 1 — CARGA Y VALIDACIÓN M5")
print("=" * 60)

files = sorted(CSV_DIR.glob("*.csv"))
print(f"\nArchivos encontrados: {len(files)}")
for f in files:
    print(f"  {f.name}")

frames = []
for f in files:
    # Saltar líneas de metadatos que empiezan con #
    df = pl.read_csv(
        f,
        comment_prefix="#",
        schema_overrides={
            "datetime": pl.String,
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "tick_volume": pl.Int64,
            "spread": pl.Int64,
            "real_volume": pl.Int64,
        },
    )
    print(f"\n  {f.name}: {len(df):,} filas")
    frames.append(df)

# Concatenar
m5 = pl.concat(frames)
print(f"\nTotal concatenado (sin depurar): {len(m5):,} filas")

# ─────────────────────────────────────────────
# 2. PARSEO Y LIMPIEZA DE DATETIME
# ─────────────────────────────────────────────
# Formato MT5: "2025.10.26 09:50:00"
m5 = m5.with_columns(
    pl.col("datetime")
    .str.strptime(pl.Datetime, "%Y.%m.%d %H:%M:%S")
    .alias("dt")
).drop("datetime")

# Ordenar cronológicamente
m5 = m5.sort("dt")

# ─────────────────────────────────────────────
# 3. VALIDACIÓN DE CALIDAD
# ─────────────────────────────────────────────
print("\n" + "─" * 50)
print("VALIDACIÓN DE CALIDAD")
print("─" * 50)

total = len(m5)

# 3a. Duplicados exactos (mismo dt)
dup_count = total - m5["dt"].n_unique()
print(f"\nDuplicados de timestamp: {dup_count}")

# Eliminar duplicados (conservar primero)
m5 = m5.unique(subset=["dt"], keep="first").sort("dt")
print(f"Filas tras eliminar duplicados: {len(m5):,}")

# 3b. Valores nulos
nulls = m5.null_count()
print(f"\nNulos por columna:\n{nulls}")

# 3c. Huecos temporales (deben ser múltiplos de 5 min)
diffs = m5.select(pl.col("dt").diff().dt.total_minutes().alias("diff_min")).drop_nulls()
gaps = diffs.filter(pl.col("diff_min") != 5)
expected_gap = 5  # minutos

gap_counts = (
    gaps.group_by("diff_min")
    .agg(pl.len().alias("count"))
    .sort("diff_min")
)
print(f"\nHuecos distintos de 5 minutos ({len(gaps):,} ocurrencias):")
print(gap_counts.head(20))

# Huecos grandes (> 30 minutos = más de 6 velas faltantes)
big_gaps = (
    m5.with_columns(pl.col("dt").diff().dt.total_minutes().alias("diff_min"))
    .filter(pl.col("diff_min") > 30)
    .select(["dt", "diff_min"])
    .sort("diff_min", descending=True)
)
print(f"\nHuecos grandes (>30 min): {len(big_gaps):,}")
print(big_gaps.head(20))

# 3d. Rangos de precios básicos
print("\nEstadísticas de precios:")
print(m5.select(["open", "high", "low", "close"]).describe())

# 3e. Verificar high >= open, close y low <= open, close
invalid_hl = m5.filter(
    (pl.col("high") < pl.col("open")) |
    (pl.col("high") < pl.col("close")) |
    (pl.col("low") > pl.col("open")) |
    (pl.col("low") > pl.col("close")) |
    (pl.col("high") < pl.col("low"))
)
print(f"\nVelas con OHLC inválido (high<low, etc.): {len(invalid_hl):,}")
if len(invalid_hl) > 0:
    print(invalid_hl.head(10))

# ─────────────────────────────────────────────
# 4. FEATURE ENGINEERING BASE
# ─────────────────────────────────────────────
print("\n" + "─" * 50)
print("FEATURES BASE (en puntos)")
print("─" * 50)

m5 = m5.with_columns([
    # Rango total de la vela en puntos
    ((pl.col("high") - pl.col("low")) / POINT).round(0).cast(pl.Int32).alias("rango_pts"),
    # Cuerpo en puntos (absoluto)
    ((pl.col("close") - pl.col("open")).abs() / POINT).round(0).cast(pl.Int32).alias("cuerpo_pts"),
    # Dirección: 1=alcista, -1=bajista, 0=doji
    pl.when(pl.col("close") > pl.col("open")).then(pl.lit(1))
      .when(pl.col("close") < pl.col("open")).then(pl.lit(-1))
      .otherwise(pl.lit(0))
      .alias("direccion"),
    # Retorno en puntos (close-to-close)
    ((pl.col("close") - pl.col("close").shift(1)) / POINT).round(0).alias("retorno_pts"),
    # Mecha superior e inferior en puntos
    ((pl.col("high") - pl.col("close").map_elements(lambda x: x, return_dtype=pl.Float64).shift(0)).abs() / POINT).alias("mecha_sup_raw"),
    ((pl.col("close") - pl.col("low")).abs() / POINT).alias("mecha_inf_raw"),
])

# Recalcular mechas correctamente
m5 = m5.with_columns([
    ((pl.col("high") - pl.when(pl.col("close") >= pl.col("open")).then(pl.col("close")).otherwise(pl.col("open"))) / POINT)
    .round(0).cast(pl.Int32).alias("mecha_sup_pts"),
    ((pl.when(pl.col("close") >= pl.col("open")).then(pl.col("open")).otherwise(pl.col("close")) - pl.col("low")) / POINT)
    .round(0).cast(pl.Int32).alias("mecha_inf_pts"),
]).drop(["mecha_sup_raw", "mecha_inf_raw"])

print("\nDistribución del rango de velas (puntos):")
rango_stats = m5["rango_pts"].describe()
print(rango_stats)

# Percentiles clave del rango
pcts = [50, 75, 90, 95, 99, 99.5, 99.9]
rango_arr = m5["rango_pts"].to_numpy()
print("\nPercentiles del rango de vela (puntos):")
for p in pcts:
    val = np.percentile(rango_arr, p)
    print(f"  P{p}: {val:.0f} pts")

# ─────────────────────────────────────────────
# 5. EXPLORACIÓN DE SPIKES
# ─────────────────────────────────────────────
print("\n" + "─" * 50)
print("EXPLORACIÓN DE SPIKES (en una sola vela M5)")
print("─" * 50)

# Definición inicial: spike = rango high-low de la vela >= umbral
UMBRALES = [2000, 3000, 3500, 4000, 5000, 7500, 10000, 15000]

print(f"\nTotal velas: {len(m5):,}")
print(f"\n{'Umbral (pts)':>14} {'#Spikes':>10} {'% del total':>12} {'Alcistas':>10} {'Bajistas':>10}")
print("-" * 60)
for u in UMBRALES:
    spk = m5.filter(pl.col("rango_pts") >= u)
    n = len(spk)
    pct = 100 * n / len(m5)
    alc = len(spk.filter(pl.col("direccion") == 1))
    baj = len(spk.filter(pl.col("direccion") == -1))
    print(f"  {u:>12,}  {n:>10,}  {pct:>11.2f}%  {alc:>10,}  {baj:>10,}")

# Análisis detallado con umbral 3.500 pts (punto de partida del proyecto)
SPIKE_U = 3500
print(f"\n--- Detalle spikes con umbral = {SPIKE_U:,} pts ---")
spikes = m5.filter(pl.col("rango_pts") >= SPIKE_U)
print(f"Spikes encontrados: {len(spikes):,}")
print(f"\nTop 20 velas más grandes:")
top = m5.sort("rango_pts", descending=True).head(20).select(["dt", "open", "high", "low", "close", "rango_pts", "cuerpo_pts", "direccion"])
print(top)

# Distribución de spikes por mes
spikes_mes = (
    spikes
    .with_columns(pl.col("dt").dt.strftime("%Y-%m").alias("mes"))
    .group_by("mes")
    .agg(pl.len().alias("n_spikes"))
    .sort("mes")
)
print(f"\nSpikes (≥{SPIKE_U:,} pts) por mes:")
print(spikes_mes)

# ─────────────────────────────────────────────
# 6. CONSTRUCCIÓN DE M15, H1, H4
# ─────────────────────────────────────────────
print("\n" + "─" * 50)
print("CONSTRUCCIÓN DE TEMPORALIDADES SUPERIORES")
print("─" * 50)

def resample_ohlcv(df: pl.DataFrame, every: str, label: str) -> pl.DataFrame:
    """Agrega velas M5 a temporalidad superior."""
    return (
        df.sort("dt")
        .group_by_dynamic("dt", every=every, closed="left")
        .agg([
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("tick_volume").sum().alias("tick_volume"),
            pl.col("spread").mean().alias("spread"),
        ])
        .sort("dt")
        .with_columns([
            ((pl.col("high") - pl.col("low")) / POINT).round(0).cast(pl.Int32).alias("rango_pts"),
        ])
    )

m15 = resample_ohlcv(m5, "15m", "M15")
h1  = resample_ohlcv(m5, "1h",  "H1")
h4  = resample_ohlcv(m5, "4h",  "H4")

print(f"M15: {len(m15):,} velas | {m15['dt'].min()} → {m15['dt'].max()}")
print(f"H1:  {len(h1):,} velas | {h1['dt'].min()} → {h1['dt'].max()}")
print(f"H4:  {len(h4):,} velas | {h4['dt'].min()} → {h4['dt'].max()}")

# Estadísticas de rango en temporalidades superiores
for name, df in [("M15", m15), ("H1", h1), ("H4", h4)]:
    arr = df["rango_pts"].to_numpy()
    print(f"\n{name} rango (pts) — media: {arr.mean():.0f} | P50: {np.percentile(arr,50):.0f} | P90: {np.percentile(arr,90):.0f} | P99: {np.percentile(arr,99):.0f} | max: {arr.max():.0f}")

# ─────────────────────────────────────────────
# 7. GUARDAR DATASETS PROCESADOS
# ─────────────────────────────────────────────
print("\n" + "─" * 50)
print("GUARDANDO DATASETS PROCESADOS")
print("─" * 50)

m5.write_parquet(OUT_DIR / "m5_limpio.parquet")
m15.write_parquet(OUT_DIR / "m15.parquet")
h1.write_parquet(OUT_DIR / "h1.parquet")
h4.write_parquet(OUT_DIR / "h4.parquet")
spikes.write_parquet(OUT_DIR / "spikes_3500.parquet")

print(f"  ✓ m5_limpio.parquet  ({len(m5):,} filas)")
print(f"  ✓ m15.parquet        ({len(m15):,} filas)")
print(f"  ✓ h1.parquet         ({len(h1):,} filas)")
print(f"  ✓ h4.parquet         ({len(h4):,} filas)")
print(f"  ✓ spikes_3500.parquet({len(spikes):,} filas)")

# ─────────────────────────────────────────────
# 8. ESTADÍSTICAS DE RETORNOS
# ─────────────────────────────────────────────
print("\n" + "─" * 50)
print("DISTRIBUCIÓN DE RETORNOS CLOSE-TO-CLOSE (M5)")
print("─" * 50)

ret = m5["retorno_pts"].drop_nulls().to_numpy()
print(f"  Media:    {ret.mean():.2f} pts")
print(f"  Std:      {ret.std():.2f} pts")
print(f"  Min:      {ret.min():.0f} pts")
print(f"  Max:      {ret.max():.0f} pts")
print(f"  Skew:     {float(np.mean(((ret - ret.mean())/ret.std())**3)):.4f}")
print(f"  Kurt:     {float(np.mean(((ret - ret.mean())/ret.std())**4) - 3):.4f}")

pcts_ret = [-5000, -3500, -2000, -1000, 0, 1000, 2000, 3500, 5000]
print("\nFrecuencia de retornos por banda (pts):")
total_ret = len(ret)
for i in range(len(pcts_ret) - 1):
    lo, hi = pcts_ret[i], pcts_ret[i+1]
    n = ((ret >= lo) & (ret < hi)).sum()
    print(f"  [{lo:>7}, {hi:>6}): {n:>7,}  ({100*n/total_ret:.2f}%)")

# Retornos extremos
ext_pos = (ret >= 5000).sum()
ext_neg = (ret <= -5000).sum()
print(f"\n  >= +5000 pts: {ext_pos:,}  ({100*ext_pos/total_ret:.3f}%)")
print(f"  <= -5000 pts: {ext_neg:,}  ({100*ext_neg/total_ret:.3f}%)")

print("\n" + "=" * 60)
print("ETAPA 1 COMPLETADA")
print(f"Datasets guardados en: {OUT_DIR}")
print("=" * 60)

"""
PROYECTO BREAKX 600 — ETAPA 3
Dos análisis en paralelo:
  A) TP ASIMÉTRICO: probar TP=1000,2000,3000,5000,10000 pts con distintos SL.
     Objetivo: encontrar la combinación con expectativa matemática positiva real.
  B) RETROCESO POST-SPIKE: cuánto retrocede tras el spike, si hay niveles
     típicos y si entrar después del retroceso mejora la tasa de éxito.

CALIBRACIÓN CONFIRMADA (verificada con ejemplos del usuario):
  POINT = 0.01
  1000 pts → 10.00 en precio  (97162.90 → 97172.90)
  5000 pts → 50.00 en precio  (97162.90 → 97212.90)
  10000 pts → 100.00 en precio
  Precios SIN comas de miles. Decimales intactos al sumar puntos.
"""

import polars as pl
import numpy as np
import pandas as pd
from pathlib import Path

BASE  = Path(__file__).resolve().parent.parent
OUT   = BASE / "output"
POINT = 0.01   # 1 punto = 0.01 en precio. NUNCA dividir entre 1000.

# ─────────────────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────────────────
print("=" * 70)
print("ETAPA 3 — TP ASIMÉTRICO + ANÁLISIS DE RETROCESO POST-SPIKE")
print("=" * 70)

m5 = pl.read_parquet(OUT / "m5_limpio.parquet").sort("dt")
print(f"Velas M5 cargadas: {len(m5):,}")

# Arrays numpy para simulación rápida
high_arr   = m5["high"].to_numpy()
low_arr    = m5["low"].to_numpy()
close_arr  = m5["close"].to_numpy()
open_arr   = m5["open"].to_numpy()
rango_arr  = m5["rango_pts"].to_numpy()
dir_arr    = m5["direccion"].to_numpy()
dt_arr     = m5["dt"].to_numpy()
cuerpo_arr = m5["cuerpo_pts"].to_numpy()
N = len(m5)

SPIKE_U   = 3500   # umbral de spike en puntos
SPREAD    = 130    # puntos (= 1.30 en precio, pagado al entrar)
MAX_VELAS = 30     # horizonte de simulación

# ─────────────────────────────────────────────────────────
# PARTE A: TP ASIMÉTRICO
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PARTE A — TP ASIMÉTRICO")
print("=" * 70)
print("Entrada: cierre de la vela spike, en la dirección del spike.")
print(f"Spread aplicado a entrada: {SPREAD} pts = {SPREAD*POINT:.2f} en precio")
print()

# Combinaciones TP/SL a probar (en puntos)
COMBOS = [
    (1000, 2000), (1000, 3000), (1000, 5000),
    (2000, 3000), (2000, 4000), (2000, 5000), (2000, 8000),
    (3000, 3000), (3000, 5000), (3000, 6000),
    (5000, 5000), (5000, 3000),
    (10000, 5000), (10000, 10000),
    (20000, 10000), (20000, 20000),
]

spike_indices = np.where(rango_arr >= SPIKE_U)[0]
# Excluir los últimos MAX_VELAS índices
spike_indices = spike_indices[spike_indices + MAX_VELAS < N]
print(f"Spikes con horizonte disponible: {len(spike_indices):,}")

def simular_tp_sl(tp_pts: int, sl_pts: int, sp_pts: int = SPREAD) -> dict:
    """Simula entrada al cierre del spike con TP y SL dados."""
    tp_p = tp_pts * POINT
    sl_p = sl_pts * POINT
    sp_p = sp_pts * POINT

    n_tp = n_sl = n_to = 0
    for idx in spike_indices:
        d = dir_arr[idx]
        if d == 0:
            continue
        entry = close_arr[idx] + (sp_p / 2 if d == 1 else -sp_p / 2)
        tp_lvl = entry + (tp_p if d == 1 else -tp_p)
        sl_lvl = entry - (sl_p if d == 1 else -sl_p)

        resultado = "TO"
        for j in range(1, MAX_VELAS + 1):
            k = idx + j
            h, l = high_arr[k], low_arr[k]
            if d == 1:
                tp_hit, sl_hit = h >= tp_lvl, l <= sl_lvl
            else:
                tp_hit, sl_hit = l <= tp_lvl, h >= sl_lvl
            if tp_hit and sl_hit:
                resultado = "SL"; break
            elif tp_hit:
                resultado = "TP"; break
            elif sl_hit:
                resultado = "SL"; break
        if resultado == "TP":   n_tp += 1
        elif resultado == "SL": n_sl += 1
        else:                   n_to += 1

    n_total = n_tp + n_sl + n_to
    pct_tp = 100 * n_tp / n_total if n_total > 0 else 0
    # EM en puntos (excluyendo timeout = 0 pts)
    em = (n_tp * tp_pts - n_sl * sl_pts) / n_total if n_total > 0 else 0
    # EM en USD a 0.10 lotes (1000 pts = $1.00)
    em_usd = em / 1000
    ratio = tp_pts / sl_pts
    # Umbral mínimo de aciertos para EM > 0 con este ratio
    umbral_win = sl_pts / (tp_pts + sl_pts) * 100
    return {
        "tp": tp_pts, "sl": sl_pts, "ratio": round(ratio, 2),
        "n": n_total, "ntp": n_tp, "nsl": n_sl, "nto": n_to,
        "pct_tp": round(pct_tp, 2),
        "umbral_win": round(umbral_win, 1),
        "em_pts": round(em, 1),
        "em_usd_010": round(em_usd, 4),
    }

print(f"\n{'TP':>7} {'SL':>7} {'Ratio':>7} {'n':>7} {'%TP':>7} {'Min%':>6} {'EM(pts)':>9} {'EM($0.10)':>10} {'Ventaja':>8}")
print("-" * 80)

resultados_a = []
for tp, sl in COMBOS:
    r = simular_tp_sl(tp, sl)
    resultados_a.append(r)
    ventaja = "✓ POSITIVO" if r["em_pts"] > 0 and r["pct_tp"] > r["umbral_win"] else "✗"
    print(f"  {tp:>5}  {sl:>5}  {r['ratio']:>6}  {r['n']:>7,}  {r['pct_tp']:>6.2f}%  {r['umbral_win']:>5.1f}%  "
          f"{r['em_pts']:>9.1f}  {r['em_usd_010']:>9.4f}  {ventaja}")

# ─────────────────────────────────────────────────────────
# PARTE B: RETROCESO POST-SPIKE
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PARTE B — RETROCESO POST-SPIKE")
print("=" * 70)
print("Para cada spike: cuánto retrocede el precio antes de continuar o revertir.")
print()

retrocesos = []
for idx in spike_indices:
    d = dir_arr[idx]
    if d == 0:
        continue
    entry_close = close_arr[idx]
    rango = rango_arr[idx]

    # Máximo retroceso observado en las siguientes 10 velas
    max_retroceso_pts = 0.0
    max_extension_pts = 0.0
    velas_hasta_retro_max = 0
    cierre_final = close_arr[min(idx + 10, N - 1)]

    for j in range(1, min(11, N - idx)):
        k = idx + j
        if d == 1:  # BUY: retroceso = baja desde el close del spike
            retro = (entry_close - low_arr[k]) / POINT
            exten = (high_arr[k] - entry_close) / POINT
        else:  # SELL: retroceso = sube desde el close del spike
            retro = (high_arr[k] - entry_close) / POINT
            exten = (entry_close - low_arr[k]) / POINT
        if retro > max_retroceso_pts:
            max_retroceso_pts = retro
            velas_hasta_retro_max = j
        if exten > max_extension_pts:
            max_extension_pts = exten

    # ¿El precio terminó en la misma dirección después de 10 velas?
    continuo = int(
        (d == 1 and cierre_final > entry_close) or
        (d == -1 and cierre_final < entry_close)
    )

    # Ratio retroceso / rango_spike
    ratio_retro = max_retroceso_pts / rango if rango > 0 else 0

    retrocesos.append({
        "idx": int(idx),
        "direccion": int(d),
        "rango_spike_pts": int(rango),
        "max_retroceso_pts": round(max_retroceso_pts, 0),
        "ratio_retro": round(ratio_retro, 3),
        "max_extension_pts": round(max_extension_pts, 0),
        "velas_retro_max": int(velas_hasta_retro_max),
        "continuo_10v": int(continuo),
    })

df_retro = pl.DataFrame(retrocesos)
print(f"Spikes analizados: {len(df_retro):,}")

# Estadísticas del retroceso
retro_arr = df_retro["max_retroceso_pts"].to_numpy()
print("\nDistribución del retroceso máximo en 10 velas post-spike (pts):")
print(f"  Media:   {retro_arr.mean():.0f} pts  = {retro_arr.mean()*POINT:.2f} en precio")
print(f"  Mediana: {np.median(retro_arr):.0f} pts")
print(f"  P25:     {np.percentile(retro_arr, 25):.0f} pts")
print(f"  P75:     {np.percentile(retro_arr, 75):.0f} pts")
print(f"  P90:     {np.percentile(retro_arr, 90):.0f} pts")
print(f"  P95:     {np.percentile(retro_arr, 95):.0f} pts")

# ¿Qué % de spikes retroceden más de X puntos?
print("\n% de spikes que retroceden MÁS de X pts en las 10 velas siguientes:")
for x in [500, 1000, 1500, 2000, 3000, 5000]:
    pct = 100 * (retro_arr > x).mean()
    print(f"  > {x:>5} pts: {pct:.1f}%  (= {x*POINT:.2f} en precio)")

# Análisis: ¿el precio continúa en dirección del spike después de 10 velas?
continuo_arr = df_retro["continuo_10v"].to_numpy()
print(f"\n% spikes donde el precio cierra EN DIRECCIÓN del spike tras 10 velas: {100*continuo_arr.mean():.1f}%")

# ¿El retroceso predice si continuará?
print("\n--- Continuación según tamaño del retroceso ---")
bins_retro = [(0, 500), (500, 1000), (1000, 2000), (2000, 3500), (3500, 6000), (6000, 99999)]
for lo, hi in bins_retro:
    mask = (retro_arr >= lo) & (retro_arr < hi)
    n = mask.sum()
    if n < 10:
        continue
    pct_cont = 100 * continuo_arr[mask].mean()
    print(f"  Retroceso {lo:>5}–{hi:>6} pts: n={n:>5,} | continúa = {pct_cont:.1f}%")

# ─────────────────────────────────────────────────────────
# PARTE C: ENTRADA TRAS RETROCESO
# Idea: esperar que el precio retroceda X pts del spike
# y entrar en la dirección original con TP/SL
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PARTE C — ENTRADA TRAS RETROCESO POST-SPIKE")
print("=" * 70)
print("Esperar retroceso de X pts desde cierre del spike, luego entrar")
print("en la misma dirección con TP=5000 pts y SL=5000 pts.")
print()

RETRO_UMBRALES = [500, 1000, 1500, 2000, 3000]
TP_C  = 5000
SL_C  = 5000

def simular_entrada_post_retroceso(retro_trigger_pts: int, tp_pts: int, sl_pts: int) -> dict:
    tp_p = tp_pts * POINT
    sl_p = sl_pts * POINT
    sp_p = SPREAD * POINT
    retro_p = retro_trigger_pts * POINT

    n_tp = n_sl = n_to = n_no_retro = 0

    for idx in spike_indices:
        d = dir_arr[idx]
        if d == 0:
            continue
        entry_spike = close_arr[idx]

        # Buscar retroceso de retro_trigger_pts en las siguientes 10 velas
        entry_price = None
        start_j = None
        for j in range(1, 11):
            k = idx + j
            if k >= N:
                break
            if d == 1:
                retro_actual = (entry_spike - low_arr[k]) / POINT
            else:
                retro_actual = (high_arr[k] - entry_spike) / POINT
            if retro_actual >= retro_trigger_pts:
                # Precio de entrada tras retroceso: nivel del trigger
                if d == 1:
                    entry_price = entry_spike - retro_p + sp_p / 2
                else:
                    entry_price = entry_spike + retro_p - sp_p / 2
                start_j = j
                break

        if entry_price is None:
            n_no_retro += 1
            continue

        # TP/SL desde la nueva entrada
        if d == 1:
            tp_lvl = entry_price + tp_p
            sl_lvl = entry_price - sl_p
        else:
            tp_lvl = entry_price - tp_p
            sl_lvl = entry_price + sl_p

        resultado = "TO"
        for j in range(start_j, MAX_VELAS + 1):
            k = idx + j
            if k >= N:
                break
            h, l = high_arr[k], low_arr[k]
            if d == 1:
                tp_hit, sl_hit = h >= tp_lvl, l <= sl_lvl
            else:
                tp_hit, sl_hit = l <= tp_lvl, h >= sl_lvl
            if tp_hit and sl_hit:
                resultado = "SL"; break
            elif tp_hit:
                resultado = "TP"; break
            elif sl_hit:
                resultado = "SL"; break

        if resultado == "TP":   n_tp += 1
        elif resultado == "SL": n_sl += 1
        else:                   n_to += 1

    n_total = n_tp + n_sl + n_to
    pct_tp = 100 * n_tp / n_total if n_total > 0 else 0
    em     = (n_tp * tp_pts - n_sl * sl_pts) / n_total if n_total > 0 else 0
    return {
        "retro_trigger": retro_trigger_pts,
        "tp": tp_pts, "sl": sl_pts,
        "n_total": n_total, "n_no_retro": n_no_retro,
        "ntp": n_tp, "nsl": n_sl, "nto": n_to,
        "pct_tp": round(pct_tp, 2),
        "em_pts": round(em, 1),
        "em_usd_010": round(em / 1000, 4),
    }

print(f"{'Retro(pts)':>11} {'Señales':>9} {'SinRetro':>9} {'%TP':>8} {'EM(pts)':>9} {'EM($0.10)':>10}")
print("-" * 60)

resultados_c = []
for rt in RETRO_UMBRALES:
    r = simular_entrada_post_retroceso(rt, TP_C, SL_C)
    resultados_c.append(r)
    print(f"  {rt:>9,}  {r['n_total']:>9,}  {r['n_no_retro']:>9,}  "
          f"{r['pct_tp']:>7.2f}%  {r['em_pts']:>9.1f}  {r['em_usd_010']:>9.4f}")

# ─────────────────────────────────────────────────────────
# ANÁLISIS DE RUPTURA DE RÉGIMEN (jul 2026 vs antes)
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANÁLISIS DE RUPTURA DE RÉGIMEN")
print("=" * 70)

# Dividir por período: antes y después de jun 2026
import datetime

# Obtener timestamps de los spikes
spike_dt = pd.DatetimeIndex(dt_arr[spike_indices])

mask_pre  = spike_dt < pd.Timestamp("2026-06-01")
mask_post = spike_dt >= pd.Timestamp("2026-06-01")

print(f"\nSpikes pre-jun 2026:  {mask_pre.sum():,}")
print(f"Spikes jun+ 2026:     {mask_post.sum():,}")

# Para cada período: simular todas las combos TP/SL
def simular_subconjunto(indices_sub, tp_pts, sl_pts):
    tp_p = tp_pts * POINT
    sl_p = sl_pts * POINT
    sp_p = SPREAD * POINT
    n_tp = n_sl = n_to = 0
    for idx in indices_sub:
        if idx + MAX_VELAS >= N:
            continue
        d = dir_arr[idx]
        if d == 0:
            continue
        entry = close_arr[idx] + (sp_p/2 if d == 1 else -sp_p/2)
        tp_lvl = entry + (tp_p if d == 1 else -tp_p)
        sl_lvl = entry - (sl_p if d == 1 else -sl_p)
        resultado = "TO"
        for j in range(1, MAX_VELAS + 1):
            k = idx + j
            h, l = high_arr[k], low_arr[k]
            if d == 1:
                tp_hit, sl_hit = h >= tp_lvl, l <= sl_lvl
            else:
                tp_hit, sl_hit = l <= tp_lvl, h >= sl_lvl
            if tp_hit and sl_hit: resultado = "SL"; break
            elif tp_hit:          resultado = "TP"; break
            elif sl_hit:          resultado = "SL"; break
        if resultado == "TP":   n_tp += 1
        elif resultado == "SL": n_sl += 1
        else:                   n_to += 1
    n = n_tp + n_sl + n_to
    pct = 100 * n_tp / n if n > 0 else 0
    em  = (n_tp * tp_pts - n_sl * sl_pts) / n if n > 0 else 0
    return n, n_tp, n_sl, n_to, round(pct, 2), round(em, 1)

print(f"\n{'Combo TP/SL':>12} | {'PRE-jun26':>30} | {'JUN26+':>30}")
print(f"{'':>12} | {'n':>7} {'%TP':>7} {'EM':>10} | {'n':>7} {'%TP':>7} {'EM':>10}")
print("-" * 70)

combos_regimen = [(1000,2000),(2000,5000),(5000,5000),(10000,5000)]
idx_pre  = spike_indices[mask_pre]
idx_post = spike_indices[mask_post]

for tp, sl in combos_regimen:
    np_, ntp_p, nsl_p, nto_p, pct_p, em_p = simular_subconjunto(idx_pre,  tp, sl)
    nq_, ntp_q, nsl_q, nto_q, pct_q, em_q = simular_subconjunto(idx_post, tp, sl)
    label = f"{tp}/{sl}"
    print(f"  {label:>10}  | {np_:>7,} {pct_p:>7.2f}% {em_p:>10.1f} | "
          f"{nq_:>7,} {pct_q:>7.2f}% {em_q:>10.1f}")

# ─────────────────────────────────────────────────────────
# GUARDAR
# ─────────────────────────────────────────────────────────
print("\n--- GUARDANDO RESULTADOS ---")

def save_df(data_list, path):
    pd.DataFrame(data_list).to_parquet(path, index=False)

save_df(resultados_a, OUT / "etapa3_tp_asimetrico.parquet")
save_df(resultados_c, OUT / "etapa3_post_retroceso.parquet")
df_retro.to_pandas().to_parquet(OUT / "etapa3_retrocesos.parquet", index=False)
print("  ✓ etapa3_tp_asimetrico.parquet")
print("  ✓ etapa3_post_retroceso.parquet")
print("  ✓ etapa3_retrocesos.parquet")

print("\n" + "=" * 70)
print("ETAPA 3 COMPLETADA")
print("=" * 70)

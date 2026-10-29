# RESULTADO — FTS Spike ruptura con ticks reales (BreakX 600 M5)
Fecha: 2026-10-29. Plan: docs/PLAN_FTS_TICKS.md (escrito antes). Ventana: 29-sep -> 27-oct-2026 (datos nuevos).

| Simulación | Operaciones | Aciertos | Puntos/op | Total (lote 0,1) |
|---|---|---|---|---|
| A: velas M1 (método original) | 188 | 72,9 % | +623 | +117 USD |
| B: ticks bid/ask reales | 188 | 71,8 % | +504 | +95 USD |

- Diferencia B - A: -119 puntos por operación (límite fijado: -150). Pérdida media con ticks: -11.002 (teórico -11.000).
- Entrada peor que la línea: mediana 131 puntos (el spread), p90 1.161 (saltos que cruzan la línea).
- Azar con ticks (200 repeticiones, mismas reglas): mediana -119 pts/op; FTS mejor que el 84 %.
**Decisión según el plan: SIGUE EN PIE -> prueba en cuenta DEMO en vivo.**

Límites: 1 mes (~188 operaciones) mide el sesgo de las velas, no prueba la ventaja por sí solo.
Las flechas se exportaron del historial (se usaron solo 10 velas después); el repintado en vivo puede diferir.
La demo en vivo es la prueba final.

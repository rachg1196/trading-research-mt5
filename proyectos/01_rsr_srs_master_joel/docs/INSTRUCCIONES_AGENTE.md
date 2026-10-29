# CLAUDE.md — RSR/SRS Trading AI

Programa externo en **Python** (no EA en MQL5) que detecta patrones **SRS (compra)** y **RSR (venta)**
de la estrategia RSR/SRS de Master Joel y opera vía MetaTrader 5. PTP (= SRS) y TPT (= RSR) son
nombres internos del usuario; Master Joel no los usa (DECISIONS D-006, D-007).

## Reglas permanentes
- Los videos originales son de solo lectura: nunca moverlos, renombrar ni modificarlos.
- Ninguna regla de trading entra al código sin evidencia audiovisual (video + tiempo) en
  `docs/STRATEGY_RULES.md`. Clasificar: EXPLÍCITA / OBSERVADA / HIPÓTESIS / CONTRADICCIÓN.
- No introducir BOS, CHoCH, SMC, indicadores ni umbrales inventados.
- Cierre a 4 velas = propuesta del usuario, no de Master Joel.
- Modo automático desactivado por defecto; operaciones reales solo con autorización expresa.
- No afirmar análisis visual si solo se procesó audio. No inventar estadísticas.
- Las 2 clases en vivo son una clase cada una, fragmentada; orden por número de PARTE.

## Documentación (`docs/`)
PROJECT.md · VIDEO_INVENTORY.md · TASKS.md · DECISIONS.md · (por crear) VIDEO_ANALYSIS.md ·
STRATEGY_RULES.md · TEST_RESULTS.md · BACKTEST_REPORT.md · RISK_RULES.md

Al empezar una sesión: leer TASKS.md y DECISIONS.md.

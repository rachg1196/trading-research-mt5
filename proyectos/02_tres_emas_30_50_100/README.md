# 02 · Estrategia de 3 EMAs (30/50/100)

**Pregunta:** ¿la estrategia de 3 EMAs alineadas supera al azar después de costes en índices sintéticos?

**Qué se construyó**
- Reglas escritas y versionadas (`docs/STRATEGY_RULES.md`, Rev. 5) y plan de backtest fijado antes de ver resultados (`docs/BACKTEST_PLAN.md`).
- Detector en Python (`emas/`) con pruebas unitarias sobre velas sintéticas (`tests/`).
- Validación: EMAs idénticas a las de MT5 (`mql5/ExportarEMAs.mq5`, `tools/comparar_emas.py`) y revisión visual de señales (`tools/validacion_visual.py`).
- Backtest sobre **41 índices × 15 temporalidades = 615 series (~135 millones de velas)**, costes leídos de MT5 (`tools/mt5_costes.py`), control al azar ×1.000, Holm sobre 15 comparaciones, reserva del 30 %.
- Escáner MQL5 multi-mercado (`mql5/EMAs_Escaner.mq5`).

**Resultado:** sin ventaja demostrada en ninguna de las 15 temporalidades (`docs/BACKTEST_REPORT.md`). Por la regla de decisión, el programa de trading no se construyó.

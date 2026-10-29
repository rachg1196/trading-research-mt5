# 01 · Patrón RSR/SRS (Master Joel): de videos a reglas a backtest

**Pregunta:** ¿la estrategia SRS (compra) / RSR (venta) que se enseña en un curso de 37 videos se puede
convertir en reglas objetivas, y esas reglas ganan después de costes?

**Qué se construyó**
- Transcripción de 37 videos con marcas de tiempo (faster-whisper) y extracción de 1.951 fotogramas (`tools/transcribe.py`, `tools/frames.py`).
- Especificación del detector en lenguaje sencillo (`docs/DETECTOR_SPEC.md`), cada regla trazada a un video y un minuto.
- Detector causal en Python (`rsr_srs/detector.py`, `rsr_srs/ztd.py`) con **47 pruebas automáticas** (`tests/`).
- Validación contra los ejemplos del propio curso (`docs/DETECTOR_VALIDATION.md`): encuentra 12 de 14 patrones a la hora correcta.
- Backtest con spread, deslizamiento y swap; control con 1.000 entradas al azar; corrección de Holm; reserva del 30 % evaluada una sola vez (`tools/backtest.py`, `docs/BACKTEST_PLAN.md`).
- Indicador MQL5 que dibuja los patrones en el gráfico (`mql5/SRS_RSR_Detector.mq5`).
- Registro de decisiones (`docs/DECISIONS.md`) e instrucciones permanentes para el agente de IA (`docs/INSTRUCCIONES_AGENTE.md`).

**Resultado:** sin ventaja demostrada. En 9 índices sintéticos y M1/M5/M15, las señales rinden lo mismo que entrar al azar (p de Holm = 1,00); los costes hacen que ambos pierdan. Informe: `docs/FINAL_REPORT.md`.

*Nota:* las reglas textuales del curso no se publican (material de terceros); solo la especificación objetiva propia.

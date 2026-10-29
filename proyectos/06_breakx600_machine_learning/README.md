# 06 · BreakX 600: estadística y machine learning

**Pregunta:** ¿después de un *spike* grande, el precio continúa lo suficiente como para operarlo, y un modelo de ML puede elegir las mejores entradas?

**Qué se construyó (pipeline por etapas)**
1. `scripts/etapa1_carga_y_validacion.py`: carga de velas M5 por trimestres, limpieza y verificación de huecos (polars).
2. `scripts/etapa2_post_spike.py`: estadística de lo que pasa después de *spikes* de 3.000 a 5.000 puntos.
3. `scripts/etapa3_tp_asimetrico_retroceso.py`: TP asimétrico y entradas en el retroceso.
4. `scripts/etapa4_modelos_y_validacion.py`: regresión logística, HistGradientBoosting y Random Forest con partición cronológica (entrenamiento / validación / prueba ciega de agosto 2026) y **validación tick a tick con bid/ask sobre 2,67 millones de ticks**.
5. `bot/bot_breakx600.py`: bot en Python conectado a MT5 que **solo opera si la cuenta es DEMO** (`bot/config.json`, sin credenciales).

Los datos (`output/`, ticks) no se incluyen: son del bróker.

# 04 · Patrón W y M (doble/triple piso y techo)

**Qué se construyó**
- Detector de W/M (`scripts/detector.py`) y ejemplos revisados a ojo (`resultados/Fase2_ejemplos_W_M.pdf`).
- Descarga y verificación de datos de 41 mercados sintéticos (`scripts/fase0_verificar_mt5.py`, `scripts/descargar_mercados*.py`).
- Simulación con saltos realistas (si un salto cruza el SL, se llena donde cae el salto) y 3 controles: ruptura simple, seguir la última vela y azar (`scripts/fase3_*.py`).
- Batería de 41 mercados y reserva (`scripts/bateria_41.py`, `scripts/bateria_reserva.py`), pruebas de filtro EMA, Fibonacci y salida por tiempo.
- Prueba de si los *spikes* se pueden anticipar (`resultados/spikes_predecibles.txt`): llegan sin memoria.
- Indicador con escáner y EA en MQL5: ver `../../mql5/indicadores/Patron_WM.mq5` y `../../mql5/asesores/Patron_WM_EA.mq5`.

**Resultado:** sin ventaja demostrada (`resultados/fase3_reporte.txt`). La W/M rinde igual que una ruptura simple; lo que se ve tras el patrón es la inercia normal del mercado.

# 03 · EA propio ADX + EMAs (BreakX 600)

**Pregunta:** un asesor experto propio (EMAs 30/50/100 + ADX/DI + CCI) tuvo una racha ganadora de dos semanas en cuenta real. ¿Fue ventaja o azar?

**Qué se hizo**
- Inventario de 11 versiones del EA y reconstrucción de cuál operó cada periodo (`docs/tabla_versiones_EA.md`), cruzando el historial de la cuenta por comentario, hora exacta de entrada, lote y SL/TP.
- Descarga de velas M1-H1 y spread real por minuto desde ticks (`scripts/descargar_datos.py`).
- Backtest de la versión ganadora y comparación con entradas al azar (`scripts/bt.py`, `scripts/rnd.py`).
- Diagnóstico de la estructura del índice con 945.000 velas M1 (`scripts/diag.py`, `docs/informe_fase3.md`): deriva constante de ±300 puntos por minuto y saltos en contra el 95,5 % de las veces, sin memoria.

**Resultado:** acierto del EA 65,7 % frente a 65,8 % esperado por azar con ese SL/TP; −735 USD en 16 meses con lote 0,1. La racha se explica por azar y por subir el lote; "dejó de funcionar" porque el spread se duplicó. `docs/CIERRE_PROYECTO.md`.

`mql5_original/` contiene versiones originales del EA solo como referencia (no tienen bloqueo de cuenta real).

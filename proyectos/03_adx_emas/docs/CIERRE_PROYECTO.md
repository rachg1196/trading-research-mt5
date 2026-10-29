# Proyecto ADX + EMAs – CERRADO: sin ventaja demostrada

Fecha de cierre: 20-oct-2026. Decisión de Raul tras la Fase 3.

## Conclusión
- La versión ganadora fue EMACEAV5.1: EMAs 30/50/100, ADX > 20, +DI > −DI, CCI ±100, SL 10.000 / TP 5.000.
- En 16 meses de backtest con spread 130 dio −$735 a lote 0,1. Acierto 65,7%, igual al 65,8% que da el azar. No supera al azar.
- BreakX 600 está construido como un juego equilibrado: deriva de 300 pts/min y saltos contra la deriva el 95,5% de las veces, imposibles de anticipar. Seguir la tendencia rinde cero antes de costes.
- La racha de ago-sep 2025 fue azar (horas en que el EA estuvo encendido) amplificado por subir el lote. El spread pasó de 65 a 130 en dic-2025.
- La reserva fuera de muestra (may-oct 2026) nunca se usó; queda intacta para cualquier estrategia futura en este símbolo.
- No se construye el programa (Fases 4 a 9 canceladas).

## Archivos
- 03_fase0: inventario, tabla de versiones, operaciones del EA, Quantum (confirmado, julio 2025) y dudosas.
- 04_datos: velas M1-H1 de BreakX 600 (ene-2025 a oct-2026) y spread real. Reutilizables en otros proyectos.
- 05_fase2: backtest de EMACEAV5.1 y comparación con el azar.
- 06_fase3: diagnóstico y estructura de BreakX 600.
- scripts: descarga de datos (solo lectura) y backtest.

## Lección para otros proyectos en sintéticos
- Antes de construir indicadores, comprobar si el símbolo tiene alguna estructura aprovechable; si es un juego equilibrado, ningún filtro lo arregla.
- Una racha de 2 semanas no prueba nada. Hay que medir contra el azar y después de costes.

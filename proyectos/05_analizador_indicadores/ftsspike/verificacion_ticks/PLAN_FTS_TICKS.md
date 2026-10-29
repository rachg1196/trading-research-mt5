# PLAN — Verificación con ticks de la regla FTS Spike ruptura (BreakX 600 M5)
Fecha: 2026-10-29. Escrito ANTES de simular.

Regla (sin cambios, la aprobada en el analizador): líneas por las 2 últimas flechas del mismo color visibles
10 velas después; línea de arriba bajista tocada -> COMPRA; línea de abajo alcista tocada -> VENTA; cada línea
una vez; SL 11.000, TP 5.000 puntos, cierre a las 48 h.
Datos: ticks bid/ask reales de BreakX 600, 29-sep -> 29-oct-2026 (datos nunca usados con esta regla).
Simulación A: con velas M1 (método original). Simulación B: tick a tick (entrada en el primer tick que cruza la
línea, al ask/bid; SL/TP en el primer tick que los cruza, al precio de ese tick).
Decisión: la regla SIGUE en pie (pasa a demo en vivo) si en B los puntos por operación son > 0 y la diferencia
B - A es mayor que -150 puntos por operación. Si no, se descarta como el SMC.
Limitación: 30 días ≈ 150-200 operaciones; sirve para medir el sesgo de las velas, no para probar la ventaja.

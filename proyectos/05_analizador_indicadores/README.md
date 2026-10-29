# 05 · Analizador de indicadores comerciales (sin código fuente)

**Pregunta:** cuatro indicadores comprados o gratuitos de los que solo existe el ejecutable (.ex5): ¿qué calculan, repintan y tienen ventaja?

**Método (sin descompilar):** scripts y EAs lectores en MQL5 que cargan el indicador con `iCustom`, leen sus buffers vela a vela y en el Probador tick a tick, y exportan a CSV para analizar en Python.

| Indicador | Qué se descubrió | Repinta | Resultado |
|---|---|---|---|
| **Quantum** | Fórmula reconstruida al 100 %: cuántas de las últimas 12 velas cerraron sobre la SMA 55 | No en velas cerradas | Gana con TP corto y SL enorme, pero el azar también; 81 % vs azar en la reserva → **no aprueba** |
| **ZeroLag** | EMA "zero lag" vs EMA; flechas = reentradas | 23 % de los cambios de tendencia en la vela abierta | Igual que lanzar una moneda en M5 → **no aprueba** |
| **Black Eagle** | Indicador de giro que llega tarde (~8.000 pts) | No en velas cerradas | Pierde en las 9 temporalidades → **no aprueba** |
| **FTS Spike** | El 77 % de las flechas en vivo desaparecen después | **Sí, mucho** | El método de rebote era una ilusión del repintado. La **ruptura** de la línea aprobó en la reserva (71 % aciertos, 99 % vs azar) |

Cada carpeta tiene los lectores MQL5 (`*_Inspector`, `*_Senales`, `*_Registro`, `*_Repintado`) y los resúmenes por fase. `ftsspike/ea/FTS_Ruptura_Demo.mq5` es el EA de la regla aprobada, **solo para cuenta demo**.

**Verificación con ticks (29-oct-2026):** en un mes de datos nuevos, la misma regla simulada tick a tick con bid/ask
reales dio +504 puntos por operación (71,8 % de aciertos, 188 operaciones) frente a +623 con velas: el sesgo de las
velas aquí es pequeño (−119 pts/op) porque el SL (11.000) es grande frente a los saltos. Mejor que el 84 % de las
entradas al azar en ese mes. Siguiente paso: prueba en cuenta demo en vivo (`ftsspike/verificacion_ticks/`).

**Probador de MT5 con ticks reales (EA real, indicador repintando en vivo), ene-oct 2026:** 2.085 operaciones,
70,3 % de aciertos, +490 USD con lote 0,1 sobre 1.000 USD, factor de beneficio 1,07, caída máxima 12,7 %.
Positiva, pero con margen pequeño: la mayor parte de la ganancia llegó en ene-mar 2026.

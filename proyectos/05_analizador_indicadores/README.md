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

**Aviso honesto:** la regla de FTS Spike se aprobó con simulación en velas M5 y relleno de saltos estimado. El proyecto posterior (`../../README.md`, "las velas pueden mentir") mostró que en estos índices la verificación tick a tick puede cambiar el resultado. Antes de usarla con dinero real hace falta esa verificación y la prueba en demo.

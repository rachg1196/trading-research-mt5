# Tabla de versiones del EA (Fase 0)

Todas usan EMAs 30/50/100, ADX 14, lote por defecto 0.10 y SL/TP en "pips" = 10 puntos (SL 1000 / TP 500 en el input = 10.000 / 5.000 puntos en BreakX 600). Ninguna tiene número mágico.

| Versión (última modificación, hora Ecuador) | Gatillo DI | ADX | CCI | Filtros extra | Reentradas | Comentario en la orden | Notas |
|---|---|---|---|---|---|---|---|
| EMACEA (21-ago-2025) | Estado: +DI > −DI (no cruce) | > 20 | 14, compra si > −100, venta si < 100 | — | Reentra en cada vela nueva mientras se cumpla la condición; 1 posición por símbolo | vacío | No compila (sintaxis iMA de MT4). Sin .ex5 |
| EMACEAV1 (22-ago-2025) | Estado | > 20 | Igual | — | Igual que EMACEA; nunca compra y vende a la vez | vacío | Primera versión funcional |
| **EMACEAV5.1 (25-ago-2025)** | Estado | > 20 | Igual | — | 1 entrada por señal; espera a que la señal desaparezca. Permite compra y venta abiertas a la vez | vacío | **Coincide con la racha ganadora** |
| EACS_TRENDV1 (9-sep-2025) | Estado | > 20 | Igual | Rango mínimo: 500 pips en 5 velas | 1 por señal | EACS_TRD | Cierre por ganancia/pérdida máx. solo del símbolo |
| EACS_TREND (10-sep-2025) | Estado | > 20 | Igual | Rango mínimo: 150 pips en 15 velas | 1 por señal | vacío | Igual que V5.1 más filtro de rango |
| EACS_TRENDV1.1 (12-sep-2025) | Estado | > 20 | Igual | Rango + confirmación DI en H1 | 1 por señal | EACS_TRD | |
| EAX (15-sep-2025) | **Cruce** DI (en vela en formación) | Opcional (0 = sin filtro) | No | Rango: 120 pips en 8 velas | 1 por cruce | EACS_ADX_EMA | La que recuerdas como "original", pero casi no operó (1 operación en el historial) |
| EACS_TRENDV2 (15-sep-2025) | Estado | > 20 | Igual | Rango + toque de línea de tendencia + vela de confirmación | 1 por señal | EACS_TRD | |
| EACS_TRENDV3 (16-sep-2025) | Estado | > 20 | Igual | V2 + TP dinámico con Order Blocks (indicador externo) | 1 por señal | EACS_TRD | |
| EACS_TRENDV1.2 (18-sep-2025) | Estado | **> 25** | **20** | — | Hasta 3 por tendencia | vacío | Defecto SL 100 / TP 100 pips |
| EACS_TRENDV1.3 (21-sep-2025) | Estado | > 25 | 20 | Ruptura de rango de 15 velas, pausa tras 2 pérdidas | Hasta 2 | FlipX_BUY / FlipX_SELL | Lote por defecto 0.01 |

Nota: la fecha es la del último guardado, no la del primer uso.

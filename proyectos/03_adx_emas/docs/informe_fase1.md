# Fase 1 – Datos (informe)

Descarga: 20-oct-2026 con scripts/descargar_datos.py (solo lectura). Archivos en 04_datos.

## Velas BreakX 600 (hora del servidor = Ecuador + 8 h)
| TF | Velas | Desde | Hasta |
|---|---|---|---|
| M1 | 945.350 | 2025-01-01 | 2026-10-20 |
| M2 | 472.694 | 2025-01-01 | 2026-10-20 |
| M5 | 189.089 | 2025-01-01 | 2026-10-20 |
| M15 | 63.060 | 2025-01-01 | 2026-10-20 |
| M30 | 31.532 | 2025-01-01 | 2026-10-20 |
| H1 | 15.769 | 2025-01-01 | 2026-10-20 |

## Calidad
- Sin duplicados, sin vacíos, sin velas incoherentes.
- 54 huecos cortos en M1 (máximo 3,1 h, mantenimiento del broker).
- Las 2.238 operaciones de BreakX 600 del historial caen dentro de sus velas M1: datos e historial coinciden en precio y horario.

## Símbolo
- Punto: 0,01. Lote mínimo: 0,1 (paso 0,01). Distancia mínima SL/TP: 390 puntos.
- Valor: 1 punto × 1 lote = $0,01. Con lote 0,1, 5.000 puntos = $5.

## Spread (coste)
- Ene-may 2025: 0 en los datos (el broker no lo registraba).
- Jun-nov 2025: 65 puntos. Fue el spread de la racha ganadora.
- Dic 2025 en adelante: 130 puntos, constante. Confirmado con 5,19 millones de ticks de los últimos 60 días (130 puntos a toda hora).
- El backtest usará 130 puntos en todo el periodo (coste actual, conservador) y mostrará también 65 puntos como referencia.

## Propuesta de división
- Desarrollo: 1-ene-2025 a 30-abr-2026 (16 meses).
- Reserva fuera de muestra: 1-may-2026 a 20-oct-2026 (5,7 meses). Se evalúa una sola vez en la Fase 7, con autorización.

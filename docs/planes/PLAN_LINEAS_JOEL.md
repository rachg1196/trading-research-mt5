# PLAN — Líneas de tendencia tipo Joel Montes (toque 3) a favor de "la pierna"

Fecha: 2026-10-26 · Aprobado por Raúl ("Ok", 19:54) · Escrito ANTES de ver cualquier resultado.
Fuente: 3 videos de Joel en `referencias\` (transcritos y revisados cuadro a cuadro).

## 1. Reglas (venta; la compra es el espejo)
**Puntos de reacción:** vela cuyo máximo supera a las 2 velas anteriores y no es superado por las 2 siguientes
(mínimo, igual hacia abajo). Se conocen 2 velas después (sin mirar el futuro).

**Línea bajista:**
- Punto 1 = un techo; punto 2 = el techo siguiente, más bajo, al menos 3 velas después.
- Tiene que haber un retroceso real entre ambos: el piso entre ellos queda ≥ 1 ATR(14) bajo el punto 2
  y ≥ 1,5 ATR bajo el punto 1.
- **Validación:** una vela CIERRA bajo ese piso (antes de cerrar sobre la línea o superar el punto 1;
  máximo 200 velas).
- **Toques:** desde la validación, cada vez que el máximo llega a la línea (margen 0,1 ATR) cuenta un toque
  (3, 4, 5, 6). Entre dos toques tiene que formarse un piso. La línea muere si una vela cierra sobre ella
  (+0,1 ATR), tras el toque 6 o 60 velas después de la validación.

**La pierna (dirección):** en la temporalidad mayor, bajista si lo último que pasó fue un cierre bajo un
piso (punto de reacción), alcista si fue un cierre sobre un techo. Se usa la última vela mayor YA cerrada.
- M2, M3, M5, M6, M10, M15 → pierna en H1.  M20, M30, H1 → pierna en H4.
- Solo se opera la línea a favor de la pierna (línea bajista solo con pierna bajista).

**Entrada:** orden límite en la línea; se llena en el primer minuto (M1) en que el precio la toca
(si abre más allá, al precio de apertura). Sin esperar cierre.
**SL:** 1 ATR(14) de esa temporalidad desde la entrada (Joel no usa SL; aquí es obligatorio).
**Salida:** al cierre de la vela del toque (variante "1 vela") o de la siguiente ("2 velas"), o en el SL.
Si en el mismo minuto se tocan entrada y SL, cuenta como SL.
Una operación abierta a la vez por dirección, temporalidad y mercado.

## 2. Variantes (fijas)
- Toques: (a) solo 3 y 4; (b) del 3 al 6.
- Salida: 1 vela / 2 velas.
- 9 temporalidades: M2, M3, M5, M6, M10, M15, M20, M30, H1.
- 2 direcciones.
- Mercados (lo que Raúl opera): BTCUSD, ETHUSD, LTCUSD, BCHUSD, DASHUSD, XRPUSDT, XAUUSD, XAGUSD, SPXUSD.
- Total: 9 × 9 × 2 × 2 × 2 = **648 pruebas** → contador global Holm 15.506 + 648 = **16.154**.
- Sintéticos de Weltrade: prueba aparte e informativa (familia Holm propia); no decide dinero.

## 3. Costes y control
- Spread real (piso = máx. mediana último año de desarrollo, mediana últimas ~7000 velas M1), swap si cruza
  la medianoche del servidor.
- Azar: 3000 entradas en minutos al azar, misma dirección, mismo SL (1 ATR) y misma salida (cierre de la
  vela de esa temporalidad o la siguiente), mismos costes. Comparación tipo Welch (p normal).

## 4. Regla de decisión (igual que siempre)
Pasa si: ≥ 30 operaciones, USD/op neto > 0, p corregida por Holm (global) < 0,05, mayoría de años positivos
y sigue positiva con spread × 1,5.
Datos: SOLO desarrollo (primer 75 % de cada mercado). La reserva (último 25 %) no se toca; se evalúa una sola
vez y solo con autorización de Raúl.

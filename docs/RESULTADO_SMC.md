# RESULTADO — Smart Money Concepts

> **ACTUALIZACION 28-10-2026 (noche): el resultado de BreakX/TrendX/SwitchX es FALSO.** Con ticks reales
> (bid/ask, 30 dias) la regla PIERDE en los 6 mercados probados: el SL lo cruzan los SALTOS del indice y se llena
> ~1.000-1.600 puntos peor que el nivel. Las velas M1 escondian eso. NO usar SMC_Ruptura_EA. Ver seccion final.
 (motor LuxAlgo = SMC_EA_LuxAlgo de Raul)

Fecha: 2026-10-28 · Plan: `PLAN_SMC.md` (escrito antes) · 3.456 pruebas.

## Mercados reales (6 criptos, oro, plata, S&P 500) — 1.728 pruebas
- **Pasan: 0.** p<0,05 sin corregir: 60 (por azar se esperan ~86). Mejores que el azar: 35 %.
- Order Block retest: el peor (solo 20 % mejor que el azar). FVG, BOS, CHoCH: peor que el azar en su mayoria.
- Lo unico algo mejor: la ruptura de estructura SWING (50 velas) en M15 (oro compras, BTC ventas) -> no pasa Holm.

## Sinteticos Weltrade — 1.728 pruebas
- **Pasan 16, TODAS en BreakX 600 M1**, salida SL = TP = 2 x ATR(14). En M15/H1 y en los demas sinteticos: nada.
- Robustez (desarrollo ene-2025 -> may-2026): 17/17 meses positivos; aguanta entrar 1-2 min tarde y el spread x2.
- **Reserva (may-2026 -> oct-2026, evaluada una vez):**
  - Compras: 4.141 ops, 68 % aciertos, +0,26 USD/op (lote 0,10), 6/6 meses +.
  - Ventas: 3.212 ops, 64,5 % aciertos, +0,27 USD/op, 6/6 meses +.
  - Spread x2: +0,13 / +0,14. Entrada 2 min tarde: +0,19 / +0,22.
- La salida del EA viejo (sin SL, TP 5000, cierre por senal contraria) PIERDE en el mismo BreakX: lo que gana es
  la salida corta y simetrica (2 ATR).

## Por que (hipotesis)
BreakX 600 es un indice sintetico: su generador parece tener "inercia" a 1 minuto (tras romper un pivote interno, el
precio sigue 2 ATR mas veces de las que vuelve). Es una propiedad del generador del broker, no de "dinero inteligente":
puede cambiar sin aviso.

## Limites
- Spread supuesto 130 puntos (especificacion); comision 0; sin deslizamiento real medido. Ver demo.
- Solo hay datos de 22 meses. TrendX/SwitchX no se probaron (sin datos).
- Ninguna prueba garantiza el futuro: el siguiente paso obligatorio es la DEMO (EA SMC_Ruptura_EA).


## Verificacion con ticks reales (30 dias, 29-sep -> 29-oct-2026)
Misma regla, simulada tick a tick con el bid/ask real (lote 0,10):

| Mercado | Compras USD/op | Ventas USD/op | Deslizamiento medio en el SL |
|---|---|---|---|
| BreakX 600 | -0,12 | -0,02 | 1.240-1.420 pts |
| TrendX 600 | -0,24 | -0,18 | 1.040-1.520 pts |
| SwitchX 600 | -0,10 | -0,02 | 1.140-1.250 pts |
| BreakX 1200 | -0,12 | -0,09 | 1.260-1.610 pts |
| TrendX 1200 | -0,11 | -0,03 | 860-1.370 pts |
| SwitchX 1200 | -0,07 | -0,22 | 1.360-1.420 pts |

El % de aciertos es el mismo que en las velas (65-79 %), pero cuando pierde, pierde casi el doble: el precio no
"pasa" por el SL, lo SALTA (un solo tick de 10-15 de precio). En velas de 1 minuto se suponia salida en el SL exacto.
Conclusion: sin ventaja. La prueba con velas M1 no sirve para estos indices con saltos; solo los ticks dicen la verdad.

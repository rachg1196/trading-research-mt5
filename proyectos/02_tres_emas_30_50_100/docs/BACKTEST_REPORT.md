# BACKTEST_REPORT — Resultado de la prueba histórica (fase 3)

Fecha: 2026-10-19 · Plan: `docs/BACKTEST_PLAN.md` (fijado antes de ver resultados, D-016) · Reglas:
`docs/STRATEGY_RULES.md` Rev. 5 · Programa: `tools/backtest.py` · Registro: D-023, D-024, D-025.

## Conclusión

**SIN VENTAJA DEMOSTRADA.** En la reserva, ninguna de las 15 temporalidades supera al control
aleatorio. Según la regla de decisión fijada antes (plan §9):
- las **fases 4 a 7 NO se ejecutan** (no hay señales en demo, ni programa, ni órdenes);
- la estrategia **no se retoca** para volver a probar con esta reserva, que ya está usada
  (`analysis/backtest/RESERVA_USADA.txt`).

## 1. Qué se probó

- **La estrategia de 3 EMAs (30/50/100)** con las reglas de STRATEGY_RULES Rev. 5 y todos los valores
  por defecto (prueba principal, la única que decide).
- **Entrada** en la apertura de la vela siguiente a la confirmación; **salida** en el cierre de la 4.ª
  vela posterior a la confirmación. Una operación abierta a la vez por símbolo y temporalidad.
- **Costes reales**:
  - spread de cada vela (o el de la especificación si es 0, o si el historial es demasiado bajo);
  - deslizamiento de 0,5 × spread al entrar y al salir;
  - swap por cada medianoche (triple los viernes);
  - comisión 0, leída de la cuenta demo.
- **Control aleatorio**: las mismas operaciones (mismo número, mismas compras y ventas, misma salida y
  mismos costes), pero con la vela de entrada elegida al azar. Se repite 1.000 veces.
- **Criterio para "supera"**, por temporalidad y con todos los símbolos juntos:
  - al menos 100 operaciones;
  - ganancia media > 0 después de costes;
  - mejor que el control con p < 0,05 después de la corrección de Holm (15 comparaciones).
- **Unidad de medida**: "vela media" (VM) = tamaño medio de las últimas 20 velas. Por ejemplo,
  −0,10 VM es perder el 10 % de una vela normal por operación. Así se pueden juntar símbolos con
  precios muy distintos.
- **Solo informativo** (no decide nada):
  - 5 variantes (V1-V5);
  - control secundario (entradas al azar solo con las EMAs alineadas);
  - entrar 1 o 3 velas tarde;
  - deslizamiento de 0 × y 1 ×.

## 2. Datos usados

- **Origen**: cuenta Weltrade DEMO, solo lectura. 41 índices sintéticos × 15 temporalidades (M1 a H4)
  = 615 series. Ninguna se excluyó.
- **Periodo**: desde la primera vela de cada serie (la más antigua es del 16-11-2023) hasta el
  18-10-2026.
- **División de cada serie por una regla de fechas fija**:
  - desarrollo = el primer 70 % del tiempo;
  - reserva = el último 30 %.
  - El corte cae entre el 02-12-2025 y el 17-08-2026, según la serie.
- **Velas**: 94,1 millones en el desarrollo y 40,4 millones en la reserva. Las 500 primeras de cada
  serie son de calentamiento.
- **Validación previa, aprobada por el usuario**:
  - EMAs y precios idénticos a los de MT5 (D-019);
  - 20 señales y 5 anulados revisados a ojo (D-023).

## 3. Resultados de la prueba principal por temporalidad

"Estrategia" y "Azar" = ganancia media por operación después de costes, en VM. "p" = fracción de las
1.000 repeticiones del azar que igualan o mejoran a la estrategia; "p Holm" = la misma, corregida por
las 15 comparaciones.

| TF | Desarrollo: ops | Desarrollo: estrategia | Desarrollo: azar | Reserva: ops | Reserva: estrategia | Reserva: azar | Reserva: p | Reserva: p Holm | Reserva: resultado |
|---|---|---|---|---|---|---|---|---|---|
| M1 | 20.094 | −0,309 | −0,310 | 8.633 | −0,306 | −0,311 | 0,42 | 1,00 | no supera |
| M2 | 11.598 | −0,198 | −0,202 | 5.026 | −0,251 | −0,204 | 0,96 | 1,00 | no supera |
| M3 | 8.536 | −0,168 | −0,160 | 3.706 | −0,187 | −0,160 | 0,81 | 1,00 | no supera |
| M4 | 6.957 | −0,172 | −0,130 | 3.066 | −0,106 | −0,130 | 0,22 | 1,00 | no supera |
| M5 | 5.844 | −0,159 | −0,114 | 2.583 | −0,128 | −0,116 | 0,62 | 1,00 | no supera |
| M6 | 5.135 | −0,126 | −0,101 | 2.165 | −0,100 | −0,101 | 0,50 | 1,00 | no supera |
| M10 | 3.572 | −0,078 | −0,074 | 1.482 | −0,112 | −0,073 | 0,85 | 1,00 | no supera |
| M12 | 3.056 | −0,092 | −0,068 | 1.256 | −0,168 | −0,067 | 0,99 | 1,00 | no supera |
| M15 | 2.368 | −0,067 | −0,059 | 1.132 | −0,021 | −0,060 | 0,20 | 1,00 | no supera |
| M20 | 1.852 | −0,132 | −0,048 | 807 | +0,042 | −0,048 | 0,03 | 0,48 | no supera |
| M30 | 1.265 | −0,054 | −0,043 | 531 | −0,044 | −0,038 | 0,55 | 1,00 | no supera |
| H1 | 664 | −0,073 | −0,028 | 292 | −0,024 | −0,025 | 0,50 | 1,00 | no supera |
| H2 | 308 | −0,093 | −0,014 | 117 | +0,004 | −0,021 | 0,42 | 1,00 | no supera |
| H3 | 200 | −0,163 | −0,023 | 96 | −0,078 | −0,010 | 0,69 | 1,00 | datos insuficientes |
| H4 | 131 | +0,011 | −0,018 | 66 | −0,394 | −0,007 | 0,99 | 1,00 | datos insuficientes |

**Cómo leerlo, en sencillo:**
- La estrategia gana o pierde **casi lo mismo que entrar al azar**, en el desarrollo y en la reserva.
  Lo que hace negativo el resultado son los costes, sobre todo en las temporalidades pequeñas: en M1,
  spread + deslizamiento cuestan unas 0,30 VM por operación.
- **M20 en la reserva** es lo más cercano a superar: +0,042 VM, p = 0,03 antes de corregir. Pero con
  15 temporalidades probadas, alguna sale así por casualidad. Después de Holm, p = 0,48, así que **no
  supera**. Además, en el desarrollo M20 era de las peores (−0,132).
- H2 queda positiva por muy poco (+0,004) y sin significación. H4, positiva en el desarrollo, cae a
  −0,394 en la reserva.
- El % de ganadoras está entre el 38 % y el 52 %. El factor de beneficio supera 1 solo en M20 (1,08) y
  en H2 (1,01) de la reserva.

## 4. Lo informativo (no cambia la conclusión)

- **Control secundario** (entradas al azar con las EMAs alineadas): da casi lo mismo que el control
  normal. El patrón no añade nada a "entrar cuando las EMAs están alineadas".
- **Variantes V1-V5** (Holm sobre 75 comparaciones): ninguna supera al control, ni en el desarrollo ni
  en la reserva. En la reserva, las mejores son de M20 (V1 p = 0,017; V3 p = 0,042; V4 p = 0,037),
  todas con p de Holm = 1,0.
- **Sensibilidad (reserva)**:
  - entrar 1 o 3 velas tarde: resultados parecidos, también negativos (M1 −0,29/−0,30; H1 −0,03/−0,03);
  - sin deslizamiento, solo M15 queda apenas positiva (+0,007 VM). Con deslizamiento 1 × todo empeora
    (M1 −0,46).
- **Por símbolo y dirección (reserva)**: 279 combinaciones tienen al menos 30 operaciones, y 57 de ellas
  (20 %) salen positivas. Con tantas combinaciones es lo esperable por azar; no se usa para nada.
- **Monte Carlo del drawdown**: la mediana y el percentil 95 están en
  `analysis/backtest/por_tf_reserva.csv` (columnas `mc_dd_*`). Con expectativa negativa, el drawdown
  crece con el número de operaciones.
- **Spread prudente** (se usó el de la especificación porque el historial era más bajo) en 18
  símbolos: BreakX, SwitchX, TrendX, SFX Vol 20-80, FX Vol 40 y los MAX.

Avisos: la comisión 0 solo se vio en operaciones de BreakX 600 de la cuenta demo, así que en los demás
símbolos es un supuesto. Los "puntos" y los USD de los CSV juntan símbolos de precios muy distintos;
para comparar, vale la columna en VM.

## 5. Archivos

- Desarrollo: `analysis/backtest/resumen_desarrollo.json`, `por_tf_desarrollo.csv`,
  `combinaciones_desarrollo.csv`.
- Reserva: `analysis/backtest/resumen_reserva.json`, `por_tf_reserva.csv`, `combinaciones_reserva.csv`.
- `RESERVA_USADA.txt`: bloqueo de la reserva, evaluada el 2026-10-19 a las 23:01.
- Detalle por serie: `analysis/backtest/desarrollo/series/` y `analysis/backtest/reserva/series/`.
- Datos y semillas: `analysis/backtest/manifiesto.json`. Costes leídos de MT5:
  `analysis/backtest/costes_mt5.json`.

# BACKTEST_PLAN — Plan de la prueba histórica (T15), fijado antes de ver resultados

Fecha: 2026-10-18 · Estado: **APROBADO con añadidos (D-021)**. Los añadidos (§8) se escribieron antes de
ejecutar nada. **EJECUTADO** (D-022): la reserva se evaluó una vez; ninguna variante supera al control →
"sin ventaja demostrada" (§8.4).
Solo backtest histórico: sin conexión operativa, sin órdenes, sin cuenta real. Datos leídos en solo lectura de
Weltrade-Demo (Demo = Real comprobado en las velas cotejadas: E2_CROSSCHECK, CLASS_CROSSCHECK).

## 0. Cómo dice el broker que se generan los precios (lectura en solo lectura, `symbol_info().description`)

| Símbolo | Descripción oficial (MT5) | Carpeta |
|---|---|---|
| FlipX 1 | "50% to change a direction, with a fixed contract step" | Synthetics |
| FlipX 2 / 3 / 4 / 5 | "50% to change a direction, random step multiplier up to x2 / x3 / x4 / x5" | Synthetics |
| FX Vol 20 / FX Vol 80 | "FX index with fixed volatility 20% / 80%" | Synthetics |
| SFX Vol 20 | "Up or Down spikes at 30 min on average, fixed volatility 20%" | Synthetics |
| BreakX 600 | "Reverse on jump level crossing, jumps about every 600 ticks" | Synthetics |

- Los campos `basis`, `category`, `exchange` y `page` vienen vacíos. La especificación no da más detalle.
- **Lectura**: según el propio broker, son **índices sintéticos generados por un proceso aleatorio**.
  - FlipX: cada paso tiene un 50 % de probabilidad de cambiar de dirección.
  - FX Vol: volatilidad fija.
  - SFX: picos aleatorios cada 30 min de media.
  - BreakX: se invierte al cruzar niveles de salto.
- **Si el proceso es aleatorio y no tiene memoria**, ningún patrón de velas debería tener ventaja después de
  costes. Por eso el **control aleatorio** es la comparación decisiva de este plan. Esto es una inferencia a
  partir de la descripción; no hemos visto el algoritmo del broker.

## 1. Qué se compara (fijado ahora)

**Detector base** para (a)-(c): los parámetros elegidos solo con los ejemplos de E2 (D-017):
- anchura 2;
- engaño 5;
- duración 24;
- vela media de 50;
- P-8 "all";
- P-9 "inside";
- mecha "b";
- S-9 y S-10.

No se ajusta nada más.

| Variante | Definición |
|---|---|
| (a) | Detector sin filtros |
| (b) | (a) + ZTD horizontal en H4 (L 50, d 1, margen 0,5; vela media H4 de 20), tal como se midió en D-019 |
| (c) | (a) + F-3 ≤ 1,0 + F-4 ≤ 0,4 (la pareja elegida con el curso en D-018) |
| (d) **CONTROL** | Entradas al azar (ver §5) |

## 2. Datos (fijado ahora)

- **Símbolos**: FlipX 1, 2, 3, 4 y 5 · FX Vol 20 · FX Vol 80 · SFX Vol 20 · BreakX 600 (nombres reales del
  servidor).
- **TF**: M1, M5 y M15. Además H4 de los mismos símbolos, solo para la variante (b).
- **Periodo común**: desde el **02-01-2025 00:00** (primera vela de BreakX 600) hasta el **17-10-2026 23:59**
  (hora del servidor).
  - Disponibilidad comprobada: FlipX 1-3 y SFX desde 2024-01; FlipX 4-5 desde 2024-07; FX Vol desde 2023-11.
- Las velas anteriores al 02-01-2025 solo se usan como calentamiento (vela media, zonas, H4); no generan
  operaciones.
- Descarga en solo lectura con `tools/mt5_history.py` (puede añadir el símbolo a Market Watch; autorizado en
  D-014). Sin órdenes.

**Separación por fecha** (fijada ahora):

| Parte | Desde | Hasta | Uso |
|---|---|---|---|
| Desarrollo (≈ 70 %) | 02-01-2025 | 03-04-2026 23:59 | revisar que todo funciona y depurar errores; se puede mirar |
| **Reserva final (≈ 30 %)** | **04-04-2026** | **17-10-2026** | **no se mira hasta el final; se evalúa una sola vez** |

- Las ventanas de los videos (jun-sep 2025) y la elección de parámetros están en la parte de desarrollo. La
  reserva no se ha usado para nada.
- **Si al revisar el desarrollo aparece un error de programación**, se corrige y se documenta. **No** se
  cambian parámetros, variantes ni criterios por los resultados del desarrollo.

## 3. Entrada, salida y costes (fijado ahora)

**Entrada**:
- **Momento**: apertura de la vela siguiente a la vela 0 (`n` = 0, FR-22). Cada señal S-10 es **una
  operación**.
- **Precio**: las velas de MT5 son de precio *bid*.
  - Compra: apertura + spread de esa vela + deslizamiento.
  - Venta: apertura − deslizamiento.

**Salida principal (FR-30..FR-32)**:
- **Momento**: cierre de la **4.ª vela** posterior a la vela 0, en la misma TF.
- **Precio**:
  - Compra: cierre (bid) − deslizamiento.
  - Venta: cierre + spread de esa vela + deslizamiento.

**Salidas de Master Joel en paralelo (FR-56)**, sobre las mismas entradas:
- (i) cierre de la vela 2 (cuenta la vela de entrada);
- (ii) cierre de la vela 3 (no la cuenta) — las dos lecturas de R-51;
- (iii) cierre de la primera vela que **cierra de vuelta dentro de la zona rota** (R-43), con tope en la
  vela 4.

**Costes**:

| Coste | Cómo se aplica |
|---|---|
| Spread | El de la columna `spread` de cada vela (puntos). MT5 puede guardar ahí el spread mínimo de la vela: por eso hay deslizamiento |
| Comisión | **0**: el historial de la cuenta (365 días, 28 operaciones de BreakX 600) tiene comisión y fee 0. Se declara como supuesto (FR-51) |
| Swap | Según la especificación del símbolo (modos 2 y 5; −1 a −8), solo si la operación cruza la medianoche del servidor |
| **Deslizamiento propuesto** | **0,5 × spread de la vela**, en la entrada y en la salida. Análisis de sensibilidad, también fijado ahora: 0 × y 1 × |

**Resultados en**:
- puntos;
- dinero por 1,0 lote (contrato 1; tick 0,01 = 0,01 USD);
- dinero con los lotes de ejemplo del usuario, solo como referencia: BreakX 600 0,80 · FX Vol 20 0,01 ·
  FlipX 5 0,10.

**Operaciones solapadas**:
- **Principal**: cada señal es independiente; mide la calidad de cada señal.
- **Secundario**: una sola posición a la vez por símbolo+TF, ignorando las señales mientras está abierta
  (Q-16 sigue abierta para la ejecución).

## 4. Métricas (FR-53, FR-54)

**Por variante, símbolo, TF, dirección y mes**:
- número de operaciones;
- % ganadoras y perdedoras;
- beneficio y pérdida brutos;
- **expectativa por operación después de costes** (puntos y USD/lote);
- factor de beneficio;
- máximo drawdown.

**Monte Carlo** (solo en la reserva): remuestreo del orden de las operaciones, 1.000 veces, para estimar la
distribución del drawdown.

## 5. Control aleatorio y criterio de "supera claramente" (fijado ahora)

**Cómo se construye el control**, para cada variante × símbolo × TF × parte (desarrollo / reserva):
- Se toman **las mismas N operaciones** que la variante.
- Las velas de entrada se eligen **al azar**, de forma uniforme, entre todas las velas válidas de ese periodo.
- **Las mismas compras y ventas**: igual número de cada una que la variante.
- **Las mismas salidas, costes y deslizamiento**.
- Se repite **1.000 veces**, con semilla fija.

**Pregunta principal**, evaluada **una sola vez** en la **reserva**:
- Se responde **por variante y TF, juntando los 9 símbolos**.
- Son 3 variantes × 3 TF = **9 comparaciones**.

**"Supera claramente"** exige que se cumplan las dos condiciones:
1. la expectativa de la variante después de costes es **> 0**;
2. es mayor que la del control con **p < 0,05 después de corregir por 9 comparaciones (Holm)**. El valor p es
   la fracción de las 1.000 repeticiones del control con expectativa ≥ la de la variante.

**Otros resultados**:
- Por símbolo: solo informativo (con 81 combinaciones, alguna saldrá "buena" por azar).
- Si una variante no supera al control, se informa así, aunque su expectativa sea positiva en algún símbolo.
- La salida principal decide; las salidas FR-56 y la sensibilidad al deslizamiento se informan aparte.

## 6. Lo que este plan no hace

- No elige parámetros ni filtros nuevos.
- No mira la reserva hasta el final.
- No envía órdenes ni usa la cuenta.
- No usa el resultado para "mejorar" el detector antes de evaluar la reserva.

## 7. Entregables

- `tools/backtest.py`, con pruebas propias de los cálculos de precio, coste y salida.
- `docs/BACKTEST_REPORT.md`.
- Datos en `analysis/backtest/`.

## 8. Añadidos del usuario (D-021), fijados ANTES de ejecutar

1. **Solapamiento**. Se informan dos cosas:
   - **(A)** la expectativa por señal, con **todas** las señales. Es la que decide el criterio de §5.
   - **(B)** una **simulación de cuenta** con **máximo 1 operación abierta por símbolo y TF**: las señales que
     llegan mientras hay una abierta se ignoran. **El drawdown y el Monte Carlo salen de (B).**
   - El **control aleatorio sigue la misma regla**: en (A), N entradas al azar independientes; en (B), esas
     mismas entradas al azar pasan por la regla de "1 abierta" igual que las de la variante.
2. **Spread**:
   - Se compara el spread de la columna `spread` del historial con el spread actual de la especificación
     (`symbol_info().spread`, leído el 18-10-2026).
   - Si la mediana del historial es **menor que el 80 %** de la especificación, para ese símbolo se usa en
     cada vela **el mayor** de los dos (el más prudente), y se informa.
3. **Comisión**: 0 según el historial de la cuenta demo. **Debe verificarse en la cuenta real de Weltrade**; si
   existe, se añadirá y se repetirá el cálculo de costes. El detector no se toca.
4. **Regla de decisión**:
   - **Si ninguna variante supera al control en la reserva**, la conclusión es **"sin ventaja demostrada"** y
     **no** se modificará el detector para volver a probar con esa reserva.
   - **Si alguna lo supera**, se confirmará con **datos nuevos** antes de construir el resto (por ejemplo,
     semanas de señales en demo, sin órdenes).

**Detalles técnicos fijados también antes de ejecutar** (el plan no los definía):
- **Juntar símbolos**:
  - cada resultado se expresa además en **velas medias del símbolo y TF**: la media de máximo − mínimo en esa
    parte del periodo;
  - así se pueden sumar símbolos con precios distintos;
  - el criterio de §5 se calcula en esa unidad, y el control usa la misma.
- **Velocidad**: en el backtest el detector **no calcula las medidas de contexto** (ZTD en la misma TF y F-5).
  No intervienen en ninguna variante y son lentas. La ZTD H4 de la variante (b) se calcula aparte, con la misma
  definición (`rsr_srs/ztd.py`).
- **Swap**:
  - modo 2: el valor de la especificación en USD por lote y noche;
  - modo 5: interés anual (valor % × precio / 360) por noche;
  - no se aplica el triple swap del miércoles (supuesto declarado).

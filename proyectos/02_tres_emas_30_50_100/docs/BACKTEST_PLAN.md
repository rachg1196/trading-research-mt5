# BACKTEST_PLAN — Plan de la prueba histórica (fase 3), fijado ANTES de ver resultados

Fecha: 2026-10-19 · Estado: **APROBADO con un cambio (D-016)**: **solo la prueba principal decide**;
las variantes son informativas y nunca llevan a la fase 4.
Reglas: `docs/STRATEGY_RULES.md` Rev. 4 (aprobada). Detector: `emas/detector.py` (fase 2 aprobada).
Plantilla: `importado/BACKTEST_PLAN_anterior.md`, solo la parte genérica.

Solo es un backtest histórico. MT5 se usa en solo lectura: no se envían órdenes ni se usa la cuenta para operar.

---

## 0. Por qué el control aleatorio es la comparación decisiva

Weltrade describe sus sintéticos como índices generados por un **proceso aleatorio**: FlipX con un 50 % de
probabilidad de cambiar de dirección, FX Vol con volatilidad fija, SFX con picos aleatorios, BreakX que
se invierte en niveles de salto. Las descripciones se leerán de nuevo en este proyecto (§2).
**Si el proceso no tiene memoria, ningún patrón debería ganar después de costes.** Por eso la pregunta no
es "¿gana dinero?", sino "¿gana **más que entrar al azar** con la misma salida y los mismos costes?".

## 1. PASO PREVIO: validación con datos reales (antes de cualquier resultado)

Se hace solo con datos de la parte de **desarrollo** (§3). Nunca con la reserva.
**Si el usuario no aprueba este paso, no se sigue.**

**1.a EMAs: las mías frente a las de MT5.**
- 3 símbolos × 3 temporalidades (por ejemplo FlipX 1 M1, FX Vol 20 M15, BreakX 600 H1).
- En cada uno, 10 velas repartidas en el periodo, todas con más de 500 velas de historial previo.
- Se compara EMA 30/50/100 (exponencial, sobre el cierre).
- **Aprobado** si la diferencia es ≤ 1 punto del símbolo (`point`) en todas las velas comparadas.
  Si falla, se busca la causa (inicio del cálculo, velas que faltan) y se corrige el cálculo, no las reglas.
- Cómo leer las EMAs de MT5: la API de Python **no** da los valores de los indicadores. Hay que elegir un
  método (pregunta B-3).

**1.b Imágenes de 20 señales para revisar a ojo.**
- Se eligen **20 señales al azar**, con semilla fija, de varios símbolos y temporalidades (al menos 5
  símbolos y 5 temporalidades distintas; compras y ventas).
- Cada imagen muestra:
  - las velas;
  - las 3 EMAs con los colores de la imagen (blanca 30, amarilla 50, negra 100);
  - la zona (rectángulo azul);
  - marcas en la vela del máximo, el toque, la ruptura y la confirmación;
  - una flecha en la entrada y otra en la salida.
- Debajo de cada imagen: símbolo, temporalidad, fecha y hora, y resultado en puntos.
- El usuario marca cada imagen como **"bien" o "mal"**. Si hay alguna "mal", se busca el error de
  programación, se corrige y se generan 20 imágenes nuevas. No se ajustan parámetros por esto.
- Archivos en `analysis/validacion/`.

## 2. Datos

**Símbolos**:
- Todos los sintéticos disponibles en Weltrade (carpeta `Synthetics` de MT5: FlipX, FX Vol, SFX Vol,
  BreakX, etc.).
- Se listan con `tools/mt5_inspect.py`, que es de solo lectura. La lista exacta se guarda en
  `analysis/backtest/manifiesto.json` **antes** de ejecutar el detector y no se cambia después.
- Se excluye cualquier símbolo que no sea sintético (forex, oro, cripto, petróleo).

**Temporalidades**: M1, M2, M3, M4, M5, M6, M10, M12, M15, M20, M30, H1, H2, H3 y H4. Cada una por
separado, con sus propias EMAs.

**Descarga**:
- Con `tools/mt5_history.py`, en solo lectura. Ojo: añade el símbolo a Market Watch si no está (pregunta B-1).
- Se guardan open, high, low, close, tick_volume y spread por vela, en hora del servidor.

**Profundidad**: "Máx. barras en gráfico" está en Ilimitado (B-2). Se descarga **todo** lo que el
broker tenga, y el manifiesto anota por símbolo y temporalidad cuántas velas hay, con su fecha inicial
y final.

**Comprobaciones de calidad** (antes de nada, sin mirar resultados):
- velas repetidas;
- huecos de tiempo;
- máximo < mínimo;
- spread 0 o ausente.

Se informa por símbolo y temporalidad. Una serie con errores graves se excluye y se anota el motivo.

## 3. División de los datos: desarrollo y reserva (regla fijada ahora)

Como cada temporalidad tiene una profundidad distinta, la fecha de corte se calcula **con una regla fija
que solo usa las fechas de las velas, no los resultados**:
- **Fin del periodo**: la última vela cerrada antes de las **00:00 (hora del servidor) del día de la
  descarga**. Es el mismo para todos.
- **Inicio**: la primera vela disponible de cada símbolo y temporalidad. Las 500 primeras son de
  calentamiento.
- **Corte**: el **70 %** del tiempo entre el inicio útil (después del calentamiento) y el fin,
  redondeado a las 00:00 de ese día.
  - Desarrollo = antes del corte.
  - **Reserva = desde el corte hasta el fin (≈ 30 %)**.
- Las fechas de corte de cada símbolo y temporalidad se escriben en `manifiesto.json` y en DECISIONS.md
  **antes de ejecutar el detector**.

**Las señales de la reserva usan como calentamiento las velas del desarrollo.** Ninguna operación cruza
el corte: una señal cuya salida cae después del corte no cuenta en el desarrollo.

**La reserva se evalúa una sola vez.**
- El programa del backtest se niega a procesar la reserva sin una orden expresa.
- Al hacerlo, deja un archivo de bloqueo (`analysis/backtest/RESERVA_USADA.txt`) con la fecha. Una
  segunda evaluación queda bloqueada.
- Si en el desarrollo aparece un **error de programación**, se corrige y se documenta. **No** se cambian
  reglas, parámetros, variantes ni criterios por los resultados del desarrollo.

## 4. Qué se prueba (lista cerrada, fijada ahora)

**Prueba principal (la única que decide)**: el detector con **todos los valores por defecto** de la Rev. 4:

| Parámetro | Valor por defecto |
|---|---|
| P-01 separación | 0,25 velas medias |
| P-02 velas desde el cruce | 10 |
| P-03 y P-12 tolerancia | 0 |
| P-04 EMA | la de la misma vela |
| P-05 ruptura | por cierre |
| P-06 retroceso | solo el primero |
| P-08, P-09 y P-10 | 20 / 20 / 10 velas |
| P-11 alineación | en todas las velas del patrón |
| P-13 zona | altura > 0 |
| P-14 operaciones | una abierta a la vez |
| P-15 retraso | 0 |

**Variantes (prueba secundaria, solo informativa)**: cada una cambia **un solo** parámetro respecto a la
principal. Son estas 5 y ninguna más. **Se informan, pero no pueden llevar a la fase 4 aunque salgan
bien** (D-016).

| Variante | Cambio |
|---|---|
| V1 | P-05 = ruptura con la mecha |
| V2 | P-01 = 0 (basta el orden de las EMAs) |
| V3 | P-03 = 0,1 velas medias de tolerancia al tocar |
| V4 | P-06 = cualquier retroceso |
| V5 | P-11 = alineadas solo en la vela de confirmación |

**Sensibilidad (informativa)**: la prueba principal con señal detectada tarde, con 1 y con 3 velas de
retraso (P-15, U-5).

## 5. Entrada, salida y costes

**Entrada**: en la apertura de la vela siguiente a la de confirmación.
**Salida**: en el cierre de la 4.ª vela posterior a la de confirmación (U-4).
Las velas de MT5 son precio *bid*.

**Precios con costes**:

| | Entrada | Salida |
|---|---|---|
| Compra | apertura + spread de esa vela + deslizamiento | cierre − deslizamiento |
| Venta | apertura − deslizamiento | cierre + spread de esa vela + deslizamiento |

**Costes**:

| Coste | Cómo se aplica |
|---|---|
| Spread | El de la columna `spread` de cada vela, en puntos. Se compara con el spread actual de la especificación del símbolo: si la mediana del historial es menor que el 80 % del actual, se usa en cada vela **el mayor** de los dos (el más prudente), y se informa. **Velas con spread 0: se usa el spread actual del símbolo (D-018)** |
| Comisión | Se lee en el historial de operaciones de la cuenta (solo lectura). Si no hay datos, se supone 0 y se declara como supuesto; **debe verificarse** en la cuenta que se vaya a usar |
| Swap | Según la especificación del símbolo, solo si la operación cruza la medianoche del servidor (en H1-H4 pasa a menudo) |
| Deslizamiento | **0,5 × spread** en la entrada y en la salida. Sensibilidad: 0 × y 1 × |

**Una operación abierta a la vez** por símbolo y temporalidad (P-14), sea compra o venta. Las señales
que llegan mientras hay una abierta se ignoran.

**Unidades de resultado**:
- puntos;
- USD por 1,0 lote (con `trade_tick_value` y `trade_tick_size`);
- **velas medias** (VM) de la vela de confirmación. Esta es la que permite juntar símbolos con precios
  distintos, y es la unidad del criterio de §7.

## 6. Control aleatorio

Para cada símbolo × temporalidad × parte (desarrollo / reserva):
- **Las mismas N operaciones** que la estrategia, **el mismo número de compras y de ventas**.
- Velas de entrada elegidas **al azar** (uniforme) entre todas las velas válidas del periodo: después
  del calentamiento y con las 4 velas de salida dentro del periodo.
- **La misma salida** (4 velas), los mismos costes y el mismo deslizamiento.
- La misma regla de "una abierta a la vez".
- Resultado medido en la misma unidad (VM de la vela anterior a la entrada).
- Se repite **1.000 veces**, con **semilla fija** anotada en el manifiesto.

**Control secundario (informativo)**: igual, pero las entradas al azar se eligen solo entre velas con
las EMAs alineadas en la misma dirección (orden + separación, P-01). Sirve para ver si el patrón aporta
algo más que "comprar cuando las EMAs suben".

## 7. Criterio de "supera al control" y corrección por comparaciones múltiples

**Pregunta principal**: se evalúa **una sola vez**, en la **reserva**, con la prueba principal.
- Una comparación por **temporalidad**, juntando todos los símbolos y las dos direcciones:
  **15 comparaciones**.

Una temporalidad **supera** al control si se cumplen las tres condiciones:
1. tiene **al menos 100 operaciones** en la reserva. Con menos, la conclusión es "datos insuficientes",
   que **no** cuenta como superar;
2. la **expectativa por operación después de costes es > 0** (en VM);
3. es mayor que la del control con **p < 0,05 después de la corrección de Holm** para 15 comparaciones.
   El valor p es la fracción de las 1.000 repeticiones del control con expectativa ≥ la de la estrategia.

**Variantes V1-V5**: se evalúan igual, con Holm sobre sus propias 5 × 15 = 75 comparaciones. **Son
solo informativas: no deciden nada.**

**Por símbolo y por dirección**: solo informativo, porque con tantas combinaciones alguna saldrá
"buena" por azar. Una combinación símbolo × temporalidad × dirección solo se muestra con métricas si
tiene **al menos 30 operaciones**; si tiene menos, se marca como "insuficiente".

## 8. Métricas

**Para la prueba principal, las variantes y los controles**, por símbolo, temporalidad, dirección y en
total, en desarrollo y en reserva:
- número de operaciones y % de ganadoras;
- **expectativa por operación después de costes** (VM, puntos y USD por lote);
- beneficio y pérdida brutos, y factor de beneficio;
- máximo drawdown;
- costes medios por operación (spread, deslizamiento y swap por separado).

**Monte Carlo del drawdown** (prueba principal; en la reserva, más el desarrollo como comprobación):
- Se reordenan al azar las operaciones de cada temporalidad 1.000 veces, con semilla fija.
- Se informa la mediana y el percentil 95 del drawdown máximo, en VM y en USD por lote.

## 9. Regla de decisión (fijada ahora)

- **Si ninguna temporalidad supera al control en la reserva** (§7), la conclusión es **"sin ventaja"**:
  - **no** se construye el programa de ejecución;
  - **no** se retoca la estrategia para volver a probar con la misma reserva.
  - Esto vale aunque alguna variante, símbolo o dirección salga positiva: eso solo se informa.
- **Si alguna temporalidad lo supera**, se pasa a la **fase 4** (semanas de señales en vivo en DEMO, sin
  órdenes), **solo con las temporalidades que superaron**. Sus criterios se fijarán antes de empezarla.
- **SOLO la prueba principal (valores por defecto) decide si se pasa a la fase 4.** Las 5 variantes
  son solo informativas: se informan, pero no pueden llevar a la fase 4 aunque salgan bien (D-016).

## 10. Lo que este plan no hace

- No elige parámetros nuevos ni cambia reglas.
- No mira la reserva hasta el final, y la evalúa una sola vez.
- No envía órdenes ni usa la cuenta para operar.

## 11. Entregables

- `tools/backtest.py`. Reutiliza solo la parte estadística genérica de `importado/backtest_anterior.py`
  (costes, control aleatorio, Holm, Monte Carlo), sin importar `rsr_srs`. Tendrá pruebas propias de los
  cálculos de precio, coste, salida, control y Holm.
- `tools/validacion_visual.py` (imágenes del paso 1.b).
- `analysis/backtest/manifiesto.json` (símbolos, fechas de corte y semillas).
- `docs/BACKTEST_REPORT.md`.

## 12. Preguntas antes de ejecutar — RESPONDIDAS (D-016)

Respuestas: B-1 sí · B-2 Ilimitado, descargar todo · B-3 opción (a), script en `mql5/`, que se
muestra al usuario antes de usarlo · B-4 sí, solo MetaTrader5 y matplotlib · B-5 Weltrade DEMO, solo
lectura.

- **B-1** `tools/mt5_history.py` añade a Market Watch los símbolos que no están (`symbol_select`).
  ¿Lo autorizas? (Es el único cambio en MT5; no son órdenes.)
- **B-2** Con el límite de 100.000 velas, M1 tiene unos 70 días de historia. ¿Lo dejamos así, o
  prefieres subir tú "Máx. barras en gráfico" en MT5 antes de descargar?
- **B-3** Para comparar las EMAs con MT5 (paso 1.a), propongo una de estas dos opciones:
  - **(a)** un pequeño script MQL5 de **solo lectura** (sin órdenes) que tú arrastras a un gráfico y que
    guarda en un CSV los valores de las 3 EMAs;
  - **(b)** que tú anotes a mano, desde la "Ventana de datos" de MT5, unas 10 velas por gráfico.
  ¿Cuál prefieres?
- **B-4** ¿Me autorizas a instalar en `.venv` el paquete `MetaTrader5` (para leer MT5) y `matplotlib`
  (para las imágenes)?
- **B-5** ¿Qué cuenta de Weltrade estará abierta para descargar los datos (demo o real)? Solo se lee;
  se anotará el servidor en el manifiesto.

# DECISIONS — registro de decisiones (no se borra historial; solo se añade)

## D-001 — Alcance del proyecto (2026-10-19)
Estrategia de 3 EMAs (30/50/100) de Master Joel Montes. Solo sintéticos (FlipX, FX Vol, SFX Vol,
BreakX, etc.). Temporalidades M1 a H4, cada una por separado. Objetivo: comprobar si supera al azar
tras costes; el programa de ejecución solo se construye si lo supera (fases 3 y 4).
Fuente: instrucciones del usuario.

## D-002 — Jerarquía de fuentes (2026-10-19)
Mandan las reglas del usuario. La imagen ilustra. El material de Master Joel solo se cita como
contexto; si difiere, se pregunta al usuario. No se inventan reglas: lo no definido es parámetro.

## D-003 — Elementos de la imagen ignorados (2026-10-19)
TP, BUY, "1R" y su área sombreada son de otra persona: no forman parte de la estrategia (usuario).
Tampoco son EMAs la línea amarilla horizontal gruesa ni la línea roja horizontal (observación).

## D-004 — Colores de las EMAs (2026-10-19) — PENDIENTE
Propuesta por deducción: blanca = EMA 30, amarilla = EMA 50, negra = EMA 100. No confirmable solo con
la imagen. Pendiente de respuesta del usuario (STRATEGY_RULES Q-01).

## D-005 — Salida (2026-10-19)
Entrada a la apertura de la vela siguiente a la de confirmación; salida al cierre de la 4.ª vela
posterior a la de confirmación. Sin SL ni TP en puntos. Fuente: usuario.

## D-006 — Proyecto anterior en solo lectura (2026-10-19)
`Escritorio\proyecto videos` solo se lee; lo reutilizable se copia aquí. En la fase 1
algunas lecturas (ficha C0907-P05 y transcripciones) fueron denegadas; se trabajó con el Anexo A y
las fichas accesibles.

## D-007 — MT5 y órdenes (2026-10-19)
MT5 solo en lectura hasta la fase 6. Ninguna orden sin autorización expresa. Cuenta real solo en la
fase 7 con autorización expresa.

## D-008 — Se descarta el material externo; prohibido leer fuera de esta carpeta (2026-10-19)
Se descarta todo el material de la carpeta "proyecto videos": es de otro proyecto y no aplica
(Master Joel ya no opera así; hoy busca la oportunidad en cualquier temporalidad). Las únicas fuentes
de las reglas son las reglas del usuario y la imagen `referencias/estrategia_emas.jpg`.
Queda prohibido leer, buscar o abrir nada fuera de `Escritorio\proyecto emas`. Si hace
falta algo de fuera, se pide al usuario y él lo copia aquí. Sustituye a D-002 (en lo relativo al
material de Master Joel) y a D-006. STRATEGY_RULES pasa a Rev. 1 sin ese material. Q-02 anulada.
Fuente: usuario.

## D-009 — Colores de las EMAs y EMAs por temporalidad (2026-10-19)
Confirmado por el usuario: blanca = EMA 30, amarilla = EMA 50, negra = EMA 100 (cierra D-004 y Q-01).
Cada temporalidad (M1 a H4) calcula sus propias EMAs, por separado (Q-03).

## D-010 — Respuestas a Q-04..Q-10 (2026-10-19)
Fuente: usuario. Recogidas en STRATEGY_RULES Rev. 2 como A-1..A-7.
- Q-04: el toque a la EMA 30 en el primer retroceso es obligatorio; la vela de confirmación NO puede
  tocarla (su mínimo queda por encima de la EMA 30 de esa vela).
- Q-05: la mecha puede atravesar la zona por debajo; solo cancela un CIERRE por debajo de la zona.
- Q-06: cerrar por debajo de la EMA 50 en el primer retroceso vale, mientras no toque la EMA 100.
- Q-07: la zona es siempre la del máximo original; si en el segundo retroceso el precio llega a la
  EMA 30, el patrón se cancela.
- Q-08: vela del máximo roja o verde, igual: zona = desde max(apertura, cierre) hasta el máximo.
- Q-09: la confirmación es una vela posterior a la que rompe la zona.
- Q-10: vela media = promedio de (máximo − mínimo) de las últimas 20 velas cerradas, fijo en 20.
  Se elimina el parámetro P-16.

## D-011 — STRATEGY_RULES Rev. 3 y aprobación de la fase 1 (2026-10-19)
Fuente: usuario.
- P-01 (separación mínima) por defecto = 0,25 velas medias (la regla exige "sin estar pegadas");
  alternativas 0 / 0,1 / 0,5 / 1,0.
- P-11 (alineación) por defecto = alineadas en todas las velas del patrón, desde la vela del máximo
  hasta la de confirmación (la regla dice "sin cruzarse"); alternativa: solo en la confirmación.
- La prueba principal usa solo los valores por defecto. Qué variantes se prueban y cómo se corrigen
  las comparaciones múltiples se decide en docs/BACKTEST_PLAN.md (fase 3).
- Fase 1 APROBADA. La fase 2 no empieza hasta que el usuario copie aquí las herramientas del
  proyecto anterior.

## D-012 — Herramientas copiadas por el usuario (2026-10-19)
Fuente: usuario.
- `tools/mt5_history.py` y `tools/mt5_inspect.py`: solo lectura de MT5; se pueden usar tal cual
  (no en la fase 2).
- `importado/` es SOLO referencia: backtest_anterior.py, BACKTEST_PLAN_anterior.md,
  FUNCTIONAL_REQUIREMENTS_anterior.md, MT5_API_NOTES_anterior.md.
- backtest_anterior.py depende de rsr_srs (otra estrategia): no se ejecuta ni se importa rsr_srs.
  En la fase 3 se reutiliza solo su parte estadística genérica (costes, control aleatorio, Holm,
  Monte Carlo).
- De los documentos se toma solo lo genérico (símbolos, lotaje, costes, notas de MT5), nunca reglas
  de RSR/SRS.
- En la fase 2 no hay conexión a MT5: las pruebas usan velas inventadas.

## D-013 — Plan de la fase 2 aprobado, con añadidos (2026-10-19)
Fuente: usuario.
- EMAs: misma fórmula que el Moving Average exponencial de MT5: alfa = 2/(n+1), sobre el cierre,
  primer valor = primer cierre. Se descartan las primeras **500 velas** de cada serie como
  calentamiento: ahí no se buscan patrones. En la fase 3 se compararán con las EMAs de MT5.
- P-11: "alineadas" = orden Y separación (≥ P-01 velas medias) en TODAS las velas del patrón, desde la
  vela del máximo hasta la de confirmación. Si falla en alguna, el patrón se anula.
- Consecuencia de P-06 (no es regla nueva): con "solo el primer retroceso", después de que un patrón
  termine (señal) o se anule, no se busca otro hasta que las EMAs se crucen y se vuelvan a alinear.
- Paquetes de .venv: numpy, pandas, pytest.

## D-014 — Interpretaciones del detector (2026-10-19) — PENDIENTES DE CONFIRMAR
Detalles que las reglas no fijan y que el detector necesita. Fuente: Claude; el usuario debe
confirmarlas o cambiarlas.
1. Inicio tras el calentamiento: si en la vela 500 las EMAs ya están alineadas, se espera a un nuevo
   cruce, porque no se puede saber si el primer retroceso ya ocurrió.
2. La alineación "empieza" cuando hay orden + separación (P-01) y al menos P-02 velas desde el
   último cruce. Los toques a la EMA 30 anteriores no cuentan. Si se pierde la separación antes del
   primer toque, se espera a que vuelva (no se gasta el "primer retroceso").
3. Vela del máximo (P-07): la de máximo más alto entre el inicio de la alineación y la vela anterior
   al toque; en empate, la más reciente.
4. A-4: el segundo retroceso empieza en la vela posterior a la ruptura. La vela de ruptura no se
   anula si su mecha toca la EMA 30. (Corrige el "ambas incluidas" que añadí en la Rev. 2.)
5. Cruce = cualquier par de EMAs (30/50, 50/100, 30/100) cambia de orden respecto a la vela anterior.
6. Vela media: incluye la vela actual (velas i-19..i, todas cerradas).

## D-015 — D-014 confirmada; Rev. 4 y fase 2 APROBADAS (2026-10-19)
Fuente: usuario. Las 6 interpretaciones de D-014 se confirman tal cual. STRATEGY_RULES Rev. 4
APROBADA. FASE 2 APROBADA (detector + 32 pruebas). Empieza la fase 3, solo con el plan
(docs/BACKTEST_PLAN.md); no se ejecuta ningún backtest hasta que el usuario lo apruebe.

## D-016 — BACKTEST_PLAN aprobado; respuestas B-1..B-5 (2026-10-19)
Fuente: usuario.
- **SOLO la prueba principal (valores por defecto) decide si se pasa a la fase 4.** Las 5 variantes
  (V1-V5) son solo informativas: se informan, pero no pueden llevar a la fase 4 aunque salgan bien.
- B-1: `tools/mt5_history.py` puede añadir símbolos a Market Watch (`symbol_select`). No son órdenes.
- B-2: "Máx. barras en gráfico" = Ilimitado. Se descarga todo lo que tenga el broker; el manifiesto
  anota las velas por símbolo y temporalidad, con fecha inicial y final.
- B-3: EMAs de MT5 con un script MQL5 de solo lectura en `mql5/`, sin ninguna función de trading; se
  muestra al usuario antes de que lo use.
- B-4: en .venv solo se añaden MetaTrader5 y matplotlib.
- B-5: datos de la cuenta Weltrade DEMO, solo lectura.
- Siguiente paso autorizado: instalar paquetes, listar sintéticos, descargar el historial, crear el
  manifiesto y escribir el script MQL5. El detector NO se ejecuta todavía.

## D-017 — Datos descargados y manifiesto (2026-10-19)
Fuente: Claude, ejecutando lo autorizado en D-016. El detector NO se ha ejecutado.
- Instalados en .venv: MetaTrader5 5.0.6231 y matplotlib 3.11.2.
- `tools/mt5_inspect.py` (Weltrade-Demo, cuenta DEMO): 41 símbolos, **todos** en la carpeta
  `Synthetics`. Universo del backtest = los 41 (lista cerrada en el manifiesto).
- Descarga con `tools/mt5_history.py`, lanzada por `tools/descargar_todo.ps1`: 41 × 15 = **615 series**,
  sin errores, desde la primera vela disponible hasta la última que abre antes del 19-10-2026 00:00
  (hora del servidor, que al descargar marcaba 09:39). Los 41 símbolos quedan en Market Watch (B-1).
- Una primera ejecución en segundo plano se solapó con la segunda. Se detuvo la primera antes de que
  escribiera nada nuevo; la lista de archivos y los recuentos son los de la ejecución completa.
- Historia: FX Vol desde 2023-11; SFX, FlipX 1-3, PainX/GainX 400/800/1200 desde 2024-01; FlipX 4-5 y
  PainX/GainX 600/999 desde 2024-07; BreakX, SwitchX y TrendX desde 2025-01; PlusX, FiboX y QuadX desde
  2025-06; MAX PainX/GainX desde 2026-01. Todas las temporalidades de un símbolo empiezan el mismo
  día, sin indicios de historial incompleto.
- Calidad: 0 velas repetidas, 0 fuera de orden, 0 OHLC imposibles. Huecos de tiempo: 7-170 por serie
  M1. **Velas con spread 0**: 0 % (FX Vol) hasta ~71 % (MAX); pendiente de decisión (pregunta D-1).
- Fechas de corte 70/30 según la regla de BACKTEST_PLAN §3, en `analysis/backtest/manifiesto.json`.
  Semillas: control 20261019, Monte Carlo 20261020, imágenes 20261021.
- Script MQL5 de solo lectura: `mql5/ExportarEMAs.mq5`, pendiente de revisión del usuario.

## D-018 — Velas con spread 0 (D-1) (2026-10-19)
Fuente: usuario. En las velas cuyo spread histórico es 0, se usa el spread actual de la
especificación del símbolo (`symbol_info().spread`, leído el 19-10-2026 y guardado en el manifiesto).
El resto de la regla de spread de BACKTEST_PLAN §5 no cambia.
Comprobación del script `mql5/ExportarEMAs.mq5`: no contiene OrderSend, OrderSendAsync, CTrade,
PositionOpen, PositionClose ni la palabra "Trade" (búsqueda sin distinguir mayúsculas: 0 coincidencias).
Gráficos para comparar las EMAs (dentro del desarrollo): FlipX 1 M1 del 01-03-2025 al 08-03-2025;
FX Vol 20 M15 del 01-06-2024 al 01-06-2025; BreakX 600 H1 del 01-03-2025 al 01-03-2026.

## D-019 — Paso previo 1.a: EMAs y OHLC frente a MT5 — PASA (2026-10-19)
Fuente: `tools/comparar_emas.py`, con los 3 CSV exportados por el usuario con `mql5/ExportarEMAs.mq5`.
Resultado en `analysis/validacion/comparacion_emas.json`.
- FlipX 1 M1 (10.081 velas), FX Vol 20 M15 (35.016) y BreakX 600 H1 (8.755): todas en el desarrollo y
  todas presentes en la descarga.
- EMA 30/50/100, 10 velas repartidas (criterio del plan): diferencia máxima **0 puntos** en los 3. En
  todas las velas: ≤ 0,000001 puntos (redondeo del CSV a 8 decimales). Tolerancia: 1 punto → **PASA**.
- Open, high, low y close: diferencia **0** en todas las velas de los 3 archivos.

## D-020 — Paso previo 1.b: imágenes generadas, pendientes de revisión (2026-10-19)
Fuente: `tools/validacion_visual.py`, autorizado por el usuario. Solo periodo de desarrollo: cada serie
se corta antes de su fecha de reserva, así que el detector no ha visto la reserva. Sin resultados en
las imágenes.
- Semilla 20261021 (manifiesto). 20 señales (10 compras y 10 ventas; 15 símbolos; 12 temporalidades
  de M2 a H4; máximo 2 por símbolo y 2 por temporalidad) y 5 anulados con motivos distintos.
- Archivos: `analysis/validacion/imagenes/01..20.png`, `A1..A5.png` e `indice.csv` (fechas de cada vela
  marcada).
- Observación de Claude (no es un cambio): en A5 la "vela del máximo" es una vela pequeña justo antes
  del toque, no el máximo más alto visible, porque la alineación con separación empezó después de
  ese máximo (regla P-07 + D-014 punto 2, confirmadas). Queda para la revisión del usuario.

## D-021 — Imagen A5 MAL: corrección de la vela del máximo; Rev. 5 (2026-10-19)
Fuente: usuario, tras revisar las imágenes de D-020. Aplica U-3a ("el MÁXIMO donde empieza el
retroceso"); no es regla nueva. Caso: FlipX 2 H3, 2024-06-21. El máximo real es la vela verde alta
(2024-06-20 18:00, máximo 104744) donde empieza el retroceso a la EMA 30, no la vela pequeña de las
06:00 del día 21. Con ese máximo el precio no superó la zona: no debía haber señal.
1. **Sustituye D-014 punto 3.** Vela del máximo = la de máximo más alto desde el último cruce de EMAs
   hasta la vela anterior al primer toque a la EMA 30 (en empate, la más reciente). Nunca un máximo
   menor porque la separación llegó después.
2. Si en la vela del máximo o en cualquier vela desde ahí hasta la confirmación las EMAs no están
   ordenadas y separadas (P-01, P-11), el patrón NO vale. No se busca otro máximo.
3. P-02 (10 velas sin cruce) se comprueba en la vela de confirmación.
- **Consecuencia para D-014 punto 2** (queda sustituido): ya no hay "inicio de la alineación". Tras el
  cruce, el primer toque a la EMA 30 (con las EMAs en orden alcista) es EL retroceso, haya o no
  separación en ese momento; si el patrón falla, se espera al siguiente cruce.
- Detalles de programación de Claude (a confirmar por el usuario): la vela del cruce entra en la
  búsqueda del máximo, pero no cuenta como toque; con P-06 = "cualquiera" (variante V4) el siguiente
  máximo se busca desde la vela donde terminó el patrón anterior.
- Pruebas: nuevo caso A5 sintético (vela muy alta justo tras el cruce, sin separación) y su espejo en
  venta; 34 de 34 pasan. Comprobado aparte que sin la vela alta el mismo patrón sí da señal.
- Las imágenes se vuelven a generar (misma semilla) más `analysis/validacion/imagenes/A5_corregida.png`
  (mismo tramo de la antigua A5 con el detector corregido).

## D-022 — Qué toque es el "primer retroceso"; detalles de D-021 confirmados (2026-10-19)
Fuente: usuario. **Corrige la "consecuencia para D-014 punto 2" escrita en D-021.**
- La tendencia alcista (regla 1) = EMAs ordenadas Y en armonía (separadas, P-01). Un toque a la EMA 30
  en una vela sin orden y separación NO es un retroceso de tendencia: no cuenta y no gasta el patrón.
- "Primer retroceso" = primer toque a la EMA 30 desde el último cruce en una vela con las EMAs
  ordenadas y separadas.
- El máximo se sigue buscando desde el último cruce hasta la vela anterior a ese toque. Si en la vela
  del máximo, o después hasta la confirmación, no hay orden y separación, el patrón no vale (D-021 se
  mantiene).
- Confirmados: la vela del cruce entra en la búsqueda del máximo y no cuenta como toque; con P-06 =
  "cualquiera" (V4) el siguiente máximo se busca desde donde terminó el patrón anterior; en la A5
  antigua el máximo es la vela roja de 104744 (zona desde su apertura, 104636, hasta 104744; A-5).
- Pruebas: nueva prueba "un toque con las EMAs pegadas no gasta el patrón y el siguiente, ya con
  separación, sí cuenta" (también en venta). La prueba de "EMAs pegadas" ahora comprueba que no se
  abre ningún patrón. 35 de 35 pasan.
- Imágenes regeneradas (misma semilla) e índice actualizado; A5_corregida no cambia (en ese toque las
  EMAs ya estaban separadas).

## D-023 — Paso previo 1.b APROBADO; se ejecuta solo el desarrollo (2026-10-19)
Fuente: usuario. Todas las imágenes nuevas están BIEN, incluidas A5 y A5_corregida (separación
correcta). A2 también: sin mecha no hay zona; se mantiene P-13 = mecha > 0. **Paso previo 1.b
APROBADO.** Orden: ejecutar SOLO la parte de DESARROLLO del backtest (prueba principal, control
aleatorio, costes reales y las 5 variantes informativas). La reserva NO se toca.
- Costes leídos de MT5 en solo lectura (`tools/mt5_costes.py` -> `analysis/backtest/costes_mt5.json`):
  cuenta DEMO; 28 operaciones de sintéticos en el historial, todas con comisión 0 (BreakX 600) ->
  comisión 0 en todos (supuesto para los demás símbolos; verificar en la cuenta que se use). Swap
  triple: viernes (swap_rollover3days = 5) en los 41 símbolos.
- `tools/backtest.py` con pruebas propias (`tests/test_backtest.py`); la reserva exige
  `--autorizo-reserva` y deja `analysis/backtest/RESERVA_USADA.txt`.

## D-024 — Resultado del DESARROLLO (2026-10-19) — informativo; la reserva no se ha tocado
Fuente: `python tools\backtest.py desarrollo` (615 series, sin errores). Archivos:
`analysis/backtest/resumen_desarrollo.json`, `por_tf_desarrollo.csv`, `combinaciones_desarrollo.csv`.
- Prueba principal: **ninguna de las 15 temporalidades supera al control** (p de Holm = 1,0 en todas).
  Expectativa negativa después de costes en 14 de 15 (de −0,31 VM en M1 a −0,05 VM en M30); H4 +0,011
  VM con 131 operaciones, p = 0,41 sin corregir (no significativo). El control da valores parecidos
  (de −0,31 a −0,01 VM): la estrategia se comporta como entrar al azar, y los costes deciden el signo.
- Control secundario (EMAs alineadas al azar): mismo resultado, sin ventaja.
- Variantes V1-V5 (informativas): ninguna supera al control (p de Holm = 1,0 en las 75 comparaciones).
- Spread prudente (mediana histórica < 80 % de la especificación) en 18 símbolos: BreakX, SwitchX,
  TrendX, SFX Vol 20-80, FX Vol 40 y los MAX.
- No se cambia nada por estos resultados (plan §3). La decisión se toma solo con la reserva.

## D-025 — RESERVA evaluada (una sola vez): SIN VENTAJA DEMOSTRADA (2026-10-19)
Fuente: el usuario autoriza evaluar la reserva una sola vez; `python tools\backtest.py reserva
--autorizo-reserva`. Queda bloqueada (`analysis/backtest/RESERVA_USADA.txt`, 2026-10-19 23:01).
- Prueba principal: **ninguna de las 15 temporalidades supera al control.** 13 "no supera" y 2 "datos
  insuficientes" (H3 96 y H4 66 operaciones, < 100). La más cercana es M20 (+0,042 VM, p = 0,03 sin
  corregir, p de Holm = 0,48).
- Variantes V1-V5 y control secundario: tampoco superan (informativo).
- **Conclusión según el plan §9: "sin ventaja demostrada".** Las fases 4 a 7 NO se ejecutan. La
  estrategia no se retoca para volver a probar con esta reserva.
- Informe: `docs/BACKTEST_REPORT.md`.

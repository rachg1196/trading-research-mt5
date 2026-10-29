# DETECTOR_SPEC — Especificación del detector SRS/RSR (sin código)

Fecha: 2026-10-18 · Autor: TL · Estado: **Rev. 1** (con la revisión del usuario, D-014; Rev. 0 en D-013).
**No autoriza programar.** Fuentes: STRATEGY_RULES (reglas de Master Joel, **[MJ R-xx]**),
FUNCTIONAL_REQUIREMENTS (decisiones del usuario, **[USUARIO FR-xx]**), PATTERN_STRUCTURE Rev. 1 (ejemplos).

Cómo leerla:
- **[MJ]**: lo enseña Master Joel (con su clasificación).
- **[USUARIO]**: lo decidió el usuario.
- **[SUPUESTO S-n]**: lo tuve que concretar yo para que el paso se pueda describir sin ambigüedad. **No está
  decidido**: necesita tu visto bueno (§8).
- Ningún número de esta especificación es una regla de Master Joel. Los valores de los parámetros se miden
  en el backtest (FR-25, FR-27).

---

## 1. Qué hace y qué no hace

- **Recibe**: las velas **cerradas** de un símbolo en una temporalidad (TF). Cada pareja símbolo+TF se analiza
  por separado [USUARIO FR-12, FR-21].
- **Devuelve**: señales **SRS (compra)** o **RSR (venta)** [MJ R-04] con todos los datos de §6.
- **No hace**:
  - no envía órdenes;
  - no mira otras temporalidades;
  - no aplica filtro de tendencia [USUARIO D-008, FR-12];
  - no usa indicadores [MJ R-23; D-007];
  - no reconoce la estructura de 3 zonas [USUARIO D-012].

### 1.1 Reglas de funcionamiento [USUARIO D-014]

- **Causal**:
  - Cada vela se evalúa solo con lo que se sabía en el momento de su cierre: esa vela y las anteriores.
  - Está **prohibido** usar velas futuras para formar zonas, contar el engaño, medir o decidir.
  - El backtest y el modo en vivo siguen el mismo recorrido, vela a vela.
- **Una zona genera como máximo una señal.**
  - Cuando una zona da señal o se descarta, se cierra y no vuelve a usarse.
  - Varios candidatos (zonas en formación, en espera de engaño o de ruptura) se pueden vigilar **en
    paralelo** en el mismo símbolo y TF.
  - Qué hacer si dos candidatos confirman en la misma vela, o hay señales simultáneas, es cosa de la
    ejecución (Q-16). En el backtest se registran todas.

### 1.2 Unidad de medida: la "vela media" [USUARIO D-014]

- Todas las distancias y anchuras (P-2, F-2, F-3, F-5, F-7) se expresan **en múltiplos de la vela media**,
  no en puntos fijos. Así un mismo valor sirve en cualquier símbolo y TF.
- **Vela media** = tamaño medio (máximo − mínimo) de las **últimas N velas cerradas** del mismo símbolo y TF,
  calculado con las velas **anteriores** a la que se evalúa (regla causal).
  - **N es un parámetro** (P-7) que se mide en el backtest.
- Es solo una **escala de medida**, como una regla para medir. **No es un indicador ni una condición de
  entrada**: no genera señales ni decide la dirección. No es una regla de Master Joel; él no usa medidas
  (STRATEGY_RULES §8).
- Ejemplo de lectura: "anchura máxima = 1,5 velas medias" significa que la zona no puede medir más de 1,5
  veces el tamaño medio de las últimas N velas.

## 2. Vocabulario

| Término | Significado en el detector | Base |
|---|---|---|
| **Zona** | Grupo de velas seguidas cuyo **nivel alto** es el máximo (con mechas) y cuyo **nivel bajo** es el mínimo (con mechas) | [MJ R-16, R-18] |
| **Nivel del engaño** | Nivel bajo en SRS y nivel alto en RSR | [USUARIO D-012, R-49] |
| **Nivel de entrada** | El nivel contrario al del engaño: nivel alto en SRS y nivel bajo en RSR | [USUARIO D-012, R-49] |
| **Engaño** | Vela o velas que **sobrepasan el nivel del engaño**, con mecha o con cuerpo, y después vuelven | [MJ R-26, R-27]; mecha basta: T-24, T-25 (OBSERVADA) |
| **Vela de confirmación (vela 0)** | La primera vela que **cierra** más allá del nivel de entrada | [MJ R-33, R-34] |
| **Anchura de la zona** | Distancia entre el nivel alto y el nivel bajo | [MJ R-22] (sin medida: parámetro) |

## 3. Paso a paso (SRS = compra; RSR es el espejo exacto)

**Paso 1. Formar la zona.**
- La zona es un grupo de **al menos 2 velas seguidas** [MJ R-16 "mínimo dos velas"] cuya anchura no supera el
  tope de anchura (parámetro P-2).
- Variante para comparar: **exactamente 2 velas** (P-1).
- **Qué velas entran en la zona**: es el parámetro **P-8** (antes S-1; D-014). Los videos no lo dicen.
  - **(a) Todas las que quepan**: las velas inmediatamente anteriores al engaño, hacia atrás, sin pasar el
    tope de anchura ni el de duración total. Recoge todas las mechas del grupo [MJ R-18 "trata de agarrar
    todas las mechas"; R-21 agrupar] sin ir a mechas lejanas [MJ R-20].
  - **(b) El grupo más corto**: 2 velas.
- **Niveles de velas distintas** [USUARIO D-012; MJ C0907-P04 @ 00:14-00:29 "prefiero… Pero está bien"]:
  - El nivel alto y el nivel bajo pueden salir de **subgrupos distintos** dentro de la ventana de la zona.
  - P-3 decide si se admite. La señal registra si los niveles salieron de las mismas velas o de velas
    distintas.
  - **S-2 (aprobado, D-014)**: los dos subgrupos tienen que estar dentro de la misma ventana de duración total.

**Paso 2. Esperar el engaño.**
- Tras la zona, una vela **sobrepasa el nivel bajo** con la mecha o con el cuerpo [MJ R-26].
- **Duración del engaño** = número de velas que sobrepasan el nivel bajo. Tope **P-4**:
  - base: 1-2 velas [MJ R-27, una sola fuente];
  - variantes: 3 y 4 [USUARIO D-013].
  - Si se supera el tope, el patrón **se descarta** [USUARIO FR-27].
- Si el precio rompe primero **por el lado de entrada** (cierre por encima del nivel alto) sin que haya habido
  engaño, no hay patrón SRS con esa zona. **S-3 (aprobado)**: se descarta la zona y no se convierte en otro
  patrón.
- **S-4 (aprobado)**:
  - Si el precio vuelve a la zona y sobrepasa otra vez el nivel bajo, esas velas **se suman** a la duración del
    engaño.
  - El nivel bajo **no se recalcula** con las mechas del engaño: el engaño no forma parte de la zona.

**Paso 3. Vuelta y ruptura.**
- Después del engaño, el precio vuelve. La **primera vela que cierra por encima del nivel alto** es la vela de
  confirmación [MJ R-32, R-33].
- No vale:
  - **Una vela que solo entra en el nivel alto y cierra dentro** [MJ R-33; OBSERVADA en la operación real
    C1306-P02, vela 04:05]. Se sigue esperando.
  - **Una sola vela que cruza los dos niveles**: viene desde debajo del nivel bajo y cierra por encima del alto
    [MJ R-28; C1306-P03 @ 00:38-00:41 "nunca que saque una sola así… y que rompa los dos niveles"].
    Cómo se comprueba es el parámetro **P-9** (antes S-5; D-014):
    - **(a) Por defecto**: entre la última vela del engaño y la vela 0 tiene que haber **al menos una vela que
      cierre dentro de la zona**. Es lo más fiel a "con una vela… hasta aquí… y después con otra, quebrar"
      (C1306-P03 @ 00:04-00:41) y a la operación real: la vela de las 04:05 cierra dentro y la de las 04:10
      rompe (C1306-P02_00m30s/00m44s_extra).
    - **(b)** Solo se descarta si la propia vela 0 sobrepasa también el nivel del engaño.
    - Si no se cumple, **no hay** confirmación. Con (a), si la vela que vuelve del engaño cierra ya fuera por
      el lado de entrada, el patrón se descarta.
- Como el nivel alto ya incluye las mechas (Paso 1), cerrar por encima de él es también "quebrar la mecha"
  [MJ R-34].

**Paso 4. Topes mientras se forma** [USUARIO FR-27, Q-18]. El patrón se descarta si, antes de la vela de
confirmación, ocurre cualquiera de estas cosas:
- el engaño supera P-4;
- la anchura supera P-2;
- la duración total supera P-5, contada desde la primera vela de la zona hasta la vela de confirmación,
  ambas incluidas.

**Paso 5. Confirmación.**
- Al **cerrar** la vela 0 se emite la señal; nunca antes [USUARIO FR-20, FR-21].
- La entrada sería al primer precio disponible [USUARIO FR-22], con la ventana de 4 velas [USUARIO FR-30..FR-32].
  Es asunto de la etapa de ejecución.

**Paso 6. Medir y, según los parámetros, filtrar.**
- Cada condición de §5 **se mide y se registra siempre**.
- Que además **descarte** la señal depende del parámetro: "desactivado" o una de sus opciones.

**RSR (venta)**: es lo mismo cambiando los papeles. El engaño sobrepasa el **nivel alto** y la confirmación es
la primera vela que **cierra por debajo del nivel bajo**.

## 4. Parámetros de estructura (valores medidos en backtest; ninguno es de Master Joel)

| ID | Parámetro | Opciones | Por defecto |
|---|---|---|---|
| P-1 | Velas de la zona | rango de ≥2 · exactamente 2 | rango de ≥2 [USUARIO D-012] |
| P-2 | Anchura máxima de la zona ("pegadita" / "muy amplia", R-22) | varias opciones a medir (Q-07), en velas medias (§1.2) | **obligatorio tener un tope** (FR-27) — valor por medir |
| P-3 | Niveles de velas distintas | permitido · no permitido | permitido [USUARIO D-012] |
| P-4 | Duración máxima del engaño | 2 (base, R-27) · 3 · 4 | 2 |
| P-5 | Duración máxima total del patrón | varias opciones (FR-27) | **obligatorio** — valor por medir |
| P-6 | Mecha que sobresale de la zona ya formada (Q-02) | (a) descalifica · (b) no descalifica · (c) **no descalifica, pero eleva el nivel de entrada**: la confirmación tiene que cerrar más allá de esa mecha. La (c) es una **lectura de R-34** ("tengo que asegurarme que este quiebra la mecha también", C1306-P06 @ 00:17-00:27); Master Joel no la dice explícitamente para este caso | sin decidir: se comparan las tres (FR-24); ver S-6 |
| P-7 | N: número de velas de la vela media (§1.2) | varias opciones | valor por medir |
| P-8 | Velas de la zona (antes S-1) | (a) todas las que quepan · (b) grupo más corto (2) | (a) |
| P-9 | Una sola vela que cruza los dos niveles (antes S-5) | (a) al menos una vela que cierre dentro de la zona entre el engaño y la vela 0 · (b) solo si la vela 0 sobrepasa el nivel del engaño | (a) [USUARIO D-014] |

## 5. Condiciones que se miden siempre y pueden filtrar (Q-07, FR-25)

Todas tienen la opción **"desactivado"**. Las demás opciones se miden en el backtest. F-2, F-3, F-5 y F-7 se
expresan en **velas medias** (§1.2).

| ID | Condición | Lo que dice Master Joel | Qué se mide (propuesta) |
|---|---|---|---|
| F-1 | Movimiento previo en contra ("que venga cayendo") | R-06, C1306-P03 @ 02:41-02:47 | Recorrido y número de velas en contra antes de la zona |
| F-2 | Vela de confirmación "muy larga" | R-36, C1306-P06 @ 01:07-01:12 | Tamaño de la vela 0 comparado con la anchura de la zona |
| F-3 | Cierre lejos de la zona | R-36, R-53 | Distancia entre el cierre de la vela 0 y el nivel de entrada |
| F-4 | Rechazo en la vela de ruptura | R-35, C0907-P11 @ 01:48-01:55 | Mecha de la vela 0 que vuelve hacia la zona |
| F-5 | Obstáculo cercano | R-37, C0907-P11 @ 00:46-00:52 | Distancia a la zona o al máximo/mínimo previo más cercano en la dirección de la operación (S-7) |
| F-6 | Consolidación | R-38, E2-05 @ 05:44-06:20 | Número de veces que el precio cruza la zona antes del engaño (S-7) |
| F-7 | Cerca de la zona rota | R-30 / R-56 (contradicción C-12) | Distancia a la zona horizontal rota previa, si existe |

## 6. Qué registra cada señal

1. **Identidad**:
   - símbolo, TF y dirección (SRS/RSR);
   - apertura `T0` y cierre de la vela 0;
   - hora de detección;
   - versión de los parámetros.
2. **Estructura**:
   - velas de la zona (número, primera y última);
   - nivel alto y nivel bajo;
   - anchura;
   - si los niveles salieron de las mismas velas o de velas distintas;
   - velas y profundidad del engaño;
   - duración total;
   - datos completos de la vela 0 (apertura, máximo, mínimo y cierre);
   - velas que entraron en la zona sin confirmar.
3. **Medidas de §5**: F-1 a F-7, con su valor medido, y si alguna mecha sobresalió de la zona (P-6).
4. **Contexto, solo registro y sin filtrar** [USUARIO FR-14, FR-28, D-008]:
   - ZTD horizontal en la misma TF;
   - ZTD diagonal (línea 1-2);
   - "primer toque" (R-13);
   - campos de tendencia para S-A/S-B/S-C (TREND_REPORT §6.3).
   - El método para medir cada uno se define en el diseño del backtest (T15). No filtran.
5. **Salidas en paralelo para comparar** (solo backtest) [USUARIO FR-56, Q-04]:
   - (i) cierre al terminar la vela 4, que es la salida principal;
   - (ii) máximo 2 velas, según Master Joel [R-41]; las dos variantes de R-51, contando o sin contar la vela de
     entrada;
   - (iii) cierre cuando una vela vuelve a cerrar dentro de la zona rota [R-43].
6. **Patrones descartados**: también se guardan, con el motivo (tope, filtro, una sola vela que cruza los dos
   niveles…), para poder auditar el detector.

## 7. Casos de prueba sacados de los videos

**Limitación.** No hay datos numéricos de esas velas; solo fotogramas. Para automatizar las pruebas habrá que
**reconstruir cada caso como una serie de velas sintética**, fiel al fotograma citado, o descargar el historial
real del símbolo con autorización (T13 no lo hizo). El resultado esperado es lo que **se ve y se dice** en el
video.

Estado de los datos (D-014):
- Hay historial real descargado para los casos de E2-07/E2-08 en M15 (TC-16, TC-24) y para RSR-01 en H4.
- Los casos en M5 de las clases de junio y julio de 2025 (TC-04…TC-15, TC-17…TC-21) **no tienen datos
  accesibles** con el límite de 100.000 barras del terminal: se reconstruirán a mano, salvo que se autorice
  ampliar ese límite.

### 7.1 Deben dar señal

| # | Caso | Video @ tiempo · fotograma | Resultado esperado |
|---|---|---|---|
| TC-01 | Dibujo SRS de 2 velas | C1306-P02 @ 02:46 → C1306-P03 @ 00:00-00:07, 00:24 · C1306-P03_00m04s, 00m24s | **Compra**. Hay señal tanto con P-1 en "≥2" como en "exactamente 2". La vela que solo llega "hasta aquí" no confirma; confirma la siguiente. |
| TC-02 | Dibujo RSR de 2 velas | C0907-P03 @ 00:45-01:01 · C0907-P03_00m52s…01m01s | **Venta**. El engaño sobrepasa por arriba y la confirmación cierra bajo la base de las 2 velas. |
| TC-03 | Dibujo RSR (curso) | RSR-01 @ 00:33-01:05 · RSR-01_00m47s…01m03s | **Venta**, leído como 2 niveles (PATTERN_STRUCTURE §5.1). |
| TC-04 | **Operación real** de compra en FlipX 4 M5 | C1306-P02 @ 00:00-00:48 · C1306-P02_00m30s_extra, 00m44s_extra | **Compra**:<br>- la vela de las 04:05 entra en el nivel alto y cierra dentro: **no** confirma;<br>- la vela 0 es la de las 04:10;<br>- la entrada observada fue a las 04:15:05 (`n` = 0).<br>Ventana de 4 velas: vela 1 = 04:15 … vela 4 = 04:30, que cierra a las **04:35**. Master Joel cerró a las 04:15:28 (R-47). |
| TC-05 | Operación real de venta en FlipX 3 M5 | C1306-P04 @ 00:35-02:38 · C1306-P04_02m28s_extra | **Venta**; zona probablemente de 2 velas. La webcam tapa parte del engaño, así que el caso se reconstruye con cautela. |
| TC-06 | Compra con una vela que entra y otra que rompe | C1306-P08 @ 01:13-01:44 · C1306-P08_01m36s | **Compra**. La verde larga cierra dentro del nivel alto y la siguiente confirma. |
| TC-07 | Compra en FX Vol 20 M5 | E2-08 @ 00:47-01:00 · E2-08_01m00s_extra | **Compra**. Hay una vela de engaño y la vela marcada con un círculo cierra sobre el nivel alto. |
| TC-08 | Venta con zona de 2-3 velas | C1306-P05 @ 01:34-01:44 · C1306-P05_01m37s_extra, 01m41s_extra | **Venta**. El engaño es por mecha. |
| TC-09 | Venta con niveles de velas distintas | C0907-P04 @ 00:14-00:29 · C0907-P04_00m17s, 00m27s | Con P-3 "permitido": **venta**, registrada como "velas distintas". Con P-3 "no permitido": **sin señal**. |

### 7.2 Comprueban los parámetros

| # | Caso | Video @ tiempo · fotograma | Resultado esperado |
|---|---|---|---|
| TC-10 | Engaño de 3-4 velas | C1306-P09 @ 00:00-00:21 · C1306-P09_00m21s | Con P-4 = 2: **descartada** por el tope del engaño. Con P-4 = 3 o 4: **compra**. Él lo da por válido ("mira el patrón, aquí está"): la base 1-2 de R-27 dejaría fuera un ejemplo suyo. |
| TC-11 | Zona "muy amplia" | C1306-P05 @ 01:14-01:34 · C1306-P05_01m37s_extra (rectángulos centrales) | Con un tope de anchura estricto: **descartada**; él dice "Está muy amplio… Aquí no hubo ningún patrón". Sin tope saldría señal, por eso el tope es obligatorio. |
| TC-12 | Zona ancha dentro de una consolidación | E2-05 @ 05:44-06:20 · E2-05_05m58s, 06m07s | La estructura es válida (venta). Con P-2 estricto o F-6 activado se **descarta**. Él lo llama "feo… pero la entrada se dio". |
| TC-13 | Vela de ruptura muy larga | C1306-P06 @ 01:07-01:17 · C1306-P06_01m17s | Con F-2 o F-3 activados: **descartada** ("de arriba yo no voy a entrar"). Si viene directamente del engaño, sin una vela que cierre dentro de la zona, se descarta con P-9 (a). |
| TC-14 | Obstáculo cercano | C0907-P11 @ 00:39-00:52 · C0907-P11_00m50s | La estructura es válida (compra). Con F-5 activado se **descarta** ("muy cerca de esta línea que aquí puede rebotar"). El tercer rectángulo de 01:00-01:02 **no** se detecta, porque las 3 zonas no están implementadas. |
| TC-15 | Ruptura con rechazo | C0907-P11 @ 01:48-01:55 · C0907-P11_01m53s_extra | Con F-4 activado: **descartada** ("me dejó rechazo, entonces no es válido"). |
| TC-16 | Patrón alejado | E2-07 @ 01:37-01:45 · E2-07_01m41s | Con F-7 activado: **descartada**. Velas M15 no contables: la serie sintética es aproximada. |
| TC-17 | SRS sin caída previa | C1306-P03 @ 02:21-02:49 · C1306-P03_02m46s | Con F-1 activado: **descartada** ("no que él esté subiendo"). Es un dibujo incompleto: hay que reconstruirlo. |
| TC-18 | Mecha que sobresale: descalifica | C0907-P10 @ 01:04-01:15 · C0907-P10_01m10s_extra | Con P-6 (a): **descartada**. Con P-6 (b): señal. |
| TC-19 | Mecha que sobresale: no descalifica | C1306-P03 @ 01:06-01:11 | Con P-6 (b): señal ("no está mal"). Con P-6 (a): descartada. |
| TC-19b | Mecha en el lado de entrada que eleva el nivel | C1306-P06 @ 00:17-00:27 · C1306-P06_00m24s_extra | Con P-6 (c): solo confirma la vela que cierra más allá de la mecha; una que cierra entre el nivel alto original y la mecha **no** confirma. |
| TC-25 | Causalidad | sintético | El resultado de cada vela no cambia si se añaden velas futuras a la serie: misma señal, misma hora y mismos niveles. |
| TC-26 | Una señal por zona | sintético | Una zona que ya dio señal no vuelve a darla aunque el precio regrese y rompa otra vez. Dos zonas vigiladas en paralelo pueden dar una señal cada una. |

### 7.3 No deben dar señal

| # | Caso | Video @ tiempo · fotograma | Resultado esperado |
|---|---|---|---|
| TC-20 | Una sola vela que cruza los dos niveles | C1306-P03 @ 00:09-00:41 · C1306-P03_00m13s | **Sin señal** ("no tomen eso"). |
| TC-21 | La vela entra en la zona pero no cierra fuera | C1306-P06 @ 00:41-00:46 · C1306-P06_00m41s_extra | **Sin confirmación** mientras no cierre fuera ("si la vela no cruza… no podemos entrar"). |
| TC-22 | Ruptura del lado de entrada sin engaño previo | sin ejemplo en video (S-3) | **Sin señal**. Es una prueba sintética. |
| TC-23 | Patrón que supera el tope de duración total | sin ejemplo en video | **Descartado** por P-5. Es una prueba sintética. |
| TC-24 | Posible patrón sin engaño | E2-07 @ 01:24-01:29 · E2-07_01m36s_extra | **DUDA**: "cae, no supera esta zona" puede significar que no hubo engaño. Con S-3 no da señal. Queda marcado para revisar. |

### 7.4 Fuera del detector (no son pruebas)

- **T-37 (3 zonas)**: no se detecta [USUARIO D-012].
- **Indeterminables** (T-04, T-05, T-16, T-21, T-22, T-30, T-31, T-38): no sirven como prueba porque el
  fotograma no muestra la estructura.

## 8. Puntos que necesitan tu revisión

| ID | Supuesto | Por qué hace falta | Alternativa |
|---|---|---|---|
| S-1 | La zona agrupa todas las velas anteriores al engaño que quepan en los topes | Los videos no dicen dónde empieza la zona | Tomar el grupo más corto, de 2 velas |
| S-2 | Los subgrupos de "velas distintas" están dentro de la misma ventana de duración | Sin límite, cualquier máximo antiguo podría servir de nivel | Exigir que los subgrupos sean contiguos |
| S-3 | Una ruptura del lado de entrada sin engaño previo descarta la zona | R-26 hace del engaño la base del patrón | Registrarla como "patrón sin engaño", sin señal |
| S-4 | Una nueva salida por el lado del engaño suma velas al engaño; el engaño no amplía la zona | Hace falta para contar P-4 | Reiniciar el patrón |
| S-5 | "Una sola vela que cruza los dos niveles" = la vela 0 también sobrepasa el nivel del engaño | R-28 lo describe solo con un dibujo | Exigir al menos una vela dentro de la zona entre el engaño y la vela 0 |
| S-6 | P-6: "mecha que sobresale" = mecha más allá del nivel **de entrada** sin cierre fuera, antes de la vela 0 | Los dos ejemplos (C0907-P10, C1306-P03) no dejan claro de qué lado | Del lado del engaño, aunque ahí se confunde con el propio engaño |
| S-7 | Las medidas propuestas para F-5 y F-6 | Él no las define | Otras medidas que propongas |

Añadidos al programar (D-015). **S-8 y S-9 aprobados por el usuario en D-016**; F-7 aplazado hasta definir la
"zona horizontal rota" de FR-14.

| ID | Supuesto | Por qué hace falta | Alternativa |
|---|---|---|---|
| S-8 | Los niveles son "de las mismas velas" si las velas que fijan el máximo y el mínimo de la zona son la misma o contiguas; si no, "distintas" (P-3) | Con la zona como rango, P-3 necesitaba una definición medible | Otra regla de agrupación |
| S-9 | Tras la primera vela del engaño, una vela que **cierra dentro** de la zona cuenta como vela de vuelta, aunque su mecha o su apertura estén fuera | Sin esto fallan TC-04 (operación real) y TC-06: la vela que vuelve del engaño se cuenta como engaño (`docs/TEST_RESULTS.md`, nota 1) | Mantener la Rev. 1 (esos dos ejemplos quedan descartados) |

Estado tras D-014:
- S-1 pasa a ser el parámetro P-8 y S-5 el parámetro P-9.
- S-2, S-3, S-4 y S-7 quedan **aprobados**.
- S-6 sigue abierto; con P-6 (c) se añade una lectura alternativa.

## Historial

- **Rev. 0** (2026-10-18, TL, D-013): borrador para revisión del usuario. Sin código.
- **Rev. 1** (2026-10-18, TL, D-014): revisión del usuario.
  - §1.1: el detector es causal y cada zona da una sola señal, con candidatos vigilados en paralelo.
  - §1.2: la unidad de medida es la vela media de las últimas N velas (P-7); es una escala, no un indicador.
  - Nuevos parámetros P-8 (antes S-1) y P-9 (antes S-5, por defecto la opción "al menos una vela dentro").
  - P-6 añade la variante (c), lectura de R-34.
  - S-2, S-3, S-4 y S-7 aprobados.
  - Nuevos casos de prueba TC-19b, TC-25 y TC-26.

## 9. ZTD horizontal en la misma TF (propuesta D-018; **aprobada con ajustes y programada en D-019**: zona previa distinta de la del patrón, sentido explícito, variante informativa H1/H4, F-5 redefinido; `rsr_srs/ztd.py`)

- **Base en los videos**:
  - "solo hay dos" ZTD: la diagonal y la **horizontal**, "rompe una zona, retestea" (E2-03 @ 00:13-00:37, R-11);
  - la mejor opción es la confluencia con la diagonal (R-12);
  - la horizontal sola también vale "siempre y cuando tú tengas el patrón en esa zona" (E2-03 @ 02:51-03:11,
    R-55);
  - "Siempre tome el primer toque" (E2-05 @ 05:23, R-13).
- **Diferencia con lo que enseña**: él marca la ZTD en H4/D1. Aquí se busca en la **misma TF** del patrón por
  decisión del usuario (Q-12, D-011). Solo se mide; **no** es obligatoria.

**Definición propuesta, en lenguaje sencillo (SRS; la RSR es el espejo)**:
1. **Zona previa.** Antes del patrón, dentro de las últimas L velas, hay un grupo de al menos 2 velas que forma
   una zona: con mechas y con la misma anchura máxima que la zona del patrón. Es la misma construcción que en
   el Paso 1.
2. **Ruptura de la zona previa.** Más tarde, una vela **cierra por encima** del nivel alto de esa zona previa
   ("rompe una zona"). En una venta, cierra por debajo del nivel bajo.
3. **Retesteo.** Después de la ruptura, el precio **vuelve** a la zona previa: alguna vela llega con su mínimo
   hasta el nivel alto de la zona rota o entra en ella ("retestea"). Queda permitido un margen de
   "cerca" medido en velas medias.
4. **El patrón está en esa zona.** La zona del patrón **toca o se solapa** con la zona previa rota, o está a no
   más de d velas medias de ella ("tengas el patrón en esa zona").
5. Si se cumple todo, la señal registra **ZTD horizontal = sí**, con estos datos:
   - a qué distancia está;
   - cuántas velas pasaron desde la ruptura;
   - cuántos retesteos hubo antes. Si es el primero, **primer toque = sí** (R-13).

**Parámetros que se medirían, sin valores fijados**:
- L: cuántas velas atrás se busca la zona previa.
- d: distancia máxima entre el patrón y la zona rota.
- Margen del retesteo.

Se mediría como **filtro opcional**: cuántas señales quita, cuántos válidos suyos pierde y cuántos descartes
elimina, con la misma separación curso/clases.

**Lo que esta definición no cubre**:
- la ZTD diagonal (línea 1-2), que necesita definir el 1-2 de forma objetiva (R-08);
- la zona de TF mayor que él usa realmente.

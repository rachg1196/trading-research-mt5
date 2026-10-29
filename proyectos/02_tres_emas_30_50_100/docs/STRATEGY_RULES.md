# STRATEGY_RULES — Estrategia de 3 EMAs (30/50/100) de Master Joel Montes

Estado: **Rev. 5 — corrección del usuario (D-021), pendiente de revisar las imágenes** · Fecha: 2026-10-19
(Rev. 4 aprobada en D-015.)

Fuentes únicas (D-008):
1. **Reglas del usuario** (§2) y sus **aclaraciones** (§2.1): mandan.
2. **Imagen** `referencias/estrategia_emas.jpg` (§1): ilustra las reglas.

Nada que no esté en las reglas se convierte en regla. Lo no definido es **parámetro** (§3), con rango
**propuesto, a medir** en el backtest (fase 3).

---

## 1. La imagen de referencia

Se **ignoran** (no son de la estrategia): la etiqueta **TP** y su línea, la etiqueta **BUY** y su línea
azul discontinua, la marca **"1R"** y el área sombreada entre BUY y TP. Tampoco son EMAs: la **línea
amarilla horizontal gruesa** de abajo (es un nivel horizontal) ni la **línea roja horizontal** (precio actual).

**EMAs (confirmado por el usuario, D-009):**

| Línea | EMA |
|---|---|
| Blanca | **EMA 30** |
| Amarilla (fina) | **EMA 50** |
| Negra | **EMA 100** |

Lo que se ve en la imagen (lectura visual, sin medir):
- Las tres EMAs suben ordenadas y separadas (blanca > amarilla > negra).
- Impulso al alza → vela verde con el máximo → retroceso.
- **Zona** (rectángulo azul): la mecha superior de la vela del máximo, prolongada a la derecha.
- El retroceso toca la blanca; una mecha parece llegar cerca de la amarilla; no llega a la negra.
- El precio vuelve a subir, supera la zona, retrocede y varias velas apoyan la mecha en la zona.

## 2. Reglas del usuario (tal cual; la VENTA es el espejo exacto de la COMPRA)

- **U-1** EMAs de 30, 50 y 100 sobre el cierre. Tendencia alcista: EMA100 < EMA50 < EMA30, en
  "armonía": ordenadas, con separación entre ellas, sin estar pegadas ni cruzándose. La separación
  mínima no está definida: se mide como parámetro (P-01).
- **U-2** NO se entra cuando las EMAs se acaban de cruzar (P-02) ni cuando el precio toca la EMA (A-1).
- **U-3** Secuencia:
  - **a.** EMAs alineadas al alza; el precio hace un impulso y un MÁXIMO (donde empieza el retroceso).
  - **b.** Primer retroceso: el precio toca la EMA 30 (tocar = la mecha llega a la EMA). Si llega
    hasta la EMA 50, también vale. Si llega a la EMA 100, el patrón no vale.
  - **c.** ZONA del máximo = solo la mecha superior de la vela del máximo (desde la parte alta del
    cuerpo hasta el máximo).
  - **d.** El precio vuelve a subir y SUPERA la zona del máximo (con mecha o con cierre: P-05; por
    defecto, **cierre por encima**).
  - **e.** Segundo retroceso: una vela toca la zona (su mínimo llega a la zona) y CIERRA por encima de
    la zona o dentro de ella → **vela de confirmación**.
  - **f.** Si la vela que toca la zona cierra POR DEBAJO de la zona → patrón **cancelado**.
  - **g.** ENTRADA: a la apertura de la vela siguiente a la de confirmación.
- **U-4** SALIDA: al cierre de la **4.ª vela posterior a la de confirmación**, misma temporalidad,
  gane o pierda. Sin stop loss ni take profit en puntos.
- **U-5** Señal detectada tarde: no se reinicia el conteo. Pasó 1 vela → quedan 3; pasaron 3 → queda 1;
  4 o más → no se entra.
- **U-6** Lo no definido = parámetro medido en el backtest (separación de las EMAs, tiempo máximo entre
  pasos, si "tocar" admite cierta distancia, si cuenta el primer retroceso o cualquiera). Nunca se
  inventan reglas.
- **U-7** Cada temporalidad por separado, con **sus propias EMAs** (D-009), sin confirmar en
  temporalidades mayores. Backtest en M1, M2, M3, M4, M5, M6, M10, M12, M15, M20, M30, H1, H2, H3 y H4.
- **U-8** Solo mercados sintéticos (FlipX, FX Vol, SFX Vol, BreakX, etc.).

### 2.1 Aclaraciones del usuario (D-010; compra, la venta es el espejo)

- **A-1** (Q-04) El toque a la EMA 30 en el primer retroceso es **obligatorio**. La vela de
  confirmación **NO** puede tocar la EMA 30: su mínimo debe quedar **por encima** de la EMA 30 de esa
  misma vela.
- **A-2** (Q-05) En la vela de confirmación, la mecha puede atravesar la zona por debajo; solo se
  cancela si el **CIERRE** queda por debajo de la zona.
- **A-3** (Q-06) En el primer retroceso, cerrar por debajo de la EMA 50 **vale**, mientras no toque la
  EMA 100.
- **A-4** (Q-07) La zona es siempre la del **máximo original**, aunque el precio suba mucho tras la
  ruptura. Si en el segundo retroceso (velas **posteriores** a la ruptura, hasta la confirmación
  incluida) el precio llega a la EMA 30, el patrón se **cancela**. (Rev. 4: la Rev. 2 decía "ambas
  incluidas"; incluir la vela de ruptura lo añadí yo, no estaba en tu respuesta. Corregido y
  confirmado, D-014/D-015.)
- **A-5** (Q-08) Vela del máximo roja o verde: igual. Zona = desde max(apertura, cierre) hasta el máximo.
- **A-6** (Q-09) La vela de confirmación es **posterior** a la que rompe la zona; nunca la misma.
- **A-7** (Q-10) Vela media (VM) = promedio de (máximo − mínimo) de las **últimas 20 velas cerradas**.
  Valor **fijo** (no es parámetro).

Ejemplo de tiempos (U-3g, U-4): vela de confirmación = C. Entrada en la apertura de C+1. Salida en el
cierre de C+4. La operación dura 4 velas.

### Convenciones técnicas (para el detector, fase 2; no cambian las reglas)
- Solo velas **cerradas**; nada de velas futuras (causal).
- EMAs como el Moving Average exponencial de MT5: alfa = 2/(n+1), sobre el cierre, primer valor =
  primer cierre. Las primeras **500 velas** de cada serie son calentamiento: ahí no se buscan
  patrones (D-013).
- Distancias medidas en vela media (A-7); la media incluye la vela actual (D-014).
- "Alineadas" (P-11) = orden Y separación ≥ P-01 en todas las velas del patrón, desde la vela del
  máximo hasta la de confirmación; si falla en alguna, el patrón se anula (D-013). No se busca otro
  máximo (D-021).
- Vela del MÁXIMO (U-3a, "el máximo donde empieza el retroceso"; D-021, sustituye a D-014 n.º 3): la
  de máximo más alto desde el último cruce de EMAs (vela del cruce incluida) hasta la vela anterior
  al **primer retroceso** (en empate, la más reciente). Nunca se elige un máximo menor porque la
  separación llegó después.
- **Primer retroceso** (D-022): el primer toque a la EMA 30 desde el último cruce en una vela con las
  EMAs **ordenadas y separadas** (P-01). Un toque con las EMAs sin orden o pegadas no es retroceso de
  tendencia: no cuenta y no gasta el patrón. La vela del cruce no cuenta como toque.
- P-02 ("no se entra cuando se acaban de cruzar") se comprueba en la **vela de confirmación** (D-021).
- Consecuencia de P-06 (no es regla nueva): con "solo el primer retroceso", después de que un patrón
  termine o se anule, no se busca otro hasta que las EMAs se vuelvan a cruzar (D-013, D-021).
- Interpretaciones del detector, confirmadas por el usuario: ver D-014 (D-015), con los puntos 2 y 3
  sustituidos por D-021.
- "Zona" (compra): **techo** = máximo de la vela del máximo; **suelo** = max(apertura, cierre) de esa
  vela (A-5). Venta: espejo (mecha inferior; suelo = mínimo, techo = min(apertura, cierre)).

## 3. Parámetros (lo no definido) — rangos **propuestos, a medir**

Valor por defecto en **negrita**. La prueba principal usa solo los valores por defecto. Qué variantes
se prueban, y cómo se corrigen las comparaciones múltiples, se decide en docs/BACKTEST_PLAN.md (fase 3).

| ID | Qué no está definido | Regla | Propuesta (a medir) |
|---|---|---|---|
| P-01 | Separación mínima entre EMAs ("armonía") | U-1 | (EMA30−EMA50) y (EMA50−EMA100) ≥ k·VM, k ∈ {**0,25**, 0, 0,1, 0,5, 1,0} (la regla exige separación: "sin estar pegadas") |
| P-02 | "Se acaban de cruzar": cuántas velas sin cruce entre ningún par de EMAs (contadas en la vela de confirmación, D-021) | U-2 | ≥ n velas, n ∈ {5, **10**, 20, 50} |
| P-03 | Tolerancia de "tocar" la EMA 30 en el primer retroceso | U-3b | mínimo ≤ EMA30 + t·VM, t ∈ {**0**, 0,1, 0,25} |
| P-04 | ¿Qué valor de EMA se compara con la mecha en el primer retroceso? | U-3b | **EMA de la misma vela** (como en el gráfico) / EMA de la vela anterior |
| P-05 | Cómo se "supera" la zona | U-3d | **cierre > techo** / máximo > techo |
| P-06 | Qué retroceso cuenta (U-6) | U-3b | **solo el primero tras el último cruce** / cualquiera |
| P-07 | Cómo se elige la vela del MÁXIMO | U-3a | **la de máximo más alto desde el último cruce hasta la vela anterior al primer toque a la EMA 30** (D-021; con P-06 = cualquiera, desde donde terminó el patrón anterior) |
| P-08 | Velas máximas: del máximo al toque de EMA | U-6 | {10, **20**, 40, sin límite} |
| P-09 | Velas máximas: del toque de EMA a la ruptura | U-6 | {10, **20**, 40, sin límite} |
| P-10 | Velas máximas: de la ruptura a la vela de confirmación | U-6 | {5, **10**, 20, sin límite} |
| P-11 | ¿Deben seguir alineadas las EMAs hasta la confirmación? | U-1 | **en todas las velas del patrón, desde la vela del máximo hasta la de confirmación** ("sin cruzarse") / solo en la vela de confirmación |
| P-12 | Tolerancia para "llega a la EMA 100" (invalida) | U-3b | mínimo ≤ EMA100 + t·VM, mismo t que P-03 |
| P-13 | Altura mínima de la zona (mecha de 0 o casi 0) | U-3c | **mecha > 0** / mecha ≥ {0,05, 0,1}·VM |
| P-14 | ¿Varias operaciones a la vez en el mismo símbolo y temporalidad? | — | **no** (una cada vez) / sí |
| P-15 | Retraso de detección simulado (U-5) | U-5 | **0** / 1 / 2 / 3 velas |

(P-16 eliminado en Rev. 2: la vela media es fija, A-7.)

## 4. Lo que NO es regla
- TP, BUY, "1R" y líneas horizontales de la imagen.
- Stop loss o take profit en puntos (U-4).
- Confirmación en temporalidades mayores, o EMAs de otra temporalidad (U-7).
- Indicadores distintos de las 3 EMAs; noticias; forex, oro, cripto, petróleo (U-8).

## 5. Preguntas para el usuario

- **Q-01** — RESUELTA (D-009): blanca = EMA 30, amarilla = EMA 50, negra = EMA 100.
- **Q-02** — ANULADA (D-008). El número de retroceso se trata solo según U-6 (P-06).
- **Q-03** — RESUELTA (D-009): cada temporalidad calcula sus propias EMAs, de M1 a H4, por separado.
- **Q-04 a Q-10** — RESUELTAS (D-010): ver A-1 a A-7.

Sin preguntas abiertas.

## Historial
- Rev. 0 (2026-10-19): primer borrador.
- Rev. 1 (2026-10-19): fuentes únicas = reglas del usuario + imagen (D-008); Q-01 y Q-03 resueltas
  (D-009); Q-02 anulada; nueva P-16 / Q-10 (definición de vela media).
- Rev. 2 (2026-10-19): respuestas Q-04..Q-10 como aclaraciones A-1..A-7 (D-010); P-16 eliminado
  (vela media fija en 20 velas).
- Rev. 3 (2026-10-19): P-01 por defecto 0,25 VM; P-11 por defecto alineadas en todas las velas del
  patrón; la prueba principal usa solo los valores por defecto (variantes y corrección por
  comparaciones múltiples, en BACKTEST_PLAN). Fase 1 APROBADA (D-011).
- Rev. 4 (2026-10-19): fórmula de las EMAs y calentamiento de 500 velas; definición de "alineadas"
  (P-11); consecuencia de P-06 (D-013). A-4 corregida y otras interpretaciones del detector
  pendientes de confirmar (D-014).
- Rev. 5 (2026-10-19): corrección del usuario tras la imagen A5 (D-021): la vela del máximo se busca
  desde el último cruce hasta el primer toque a la EMA 30 (aplica U-3a; no es regla nueva); orden y
  separación obligatorios desde esa vela hasta la confirmación, sin buscar otro máximo; P-02 se mira
  en la vela de confirmación. Sustituye D-014 puntos 2 y 3.
  Completada con D-022: solo cuenta como primer retroceso un toque con las EMAs ordenadas y separadas;
  los toques con EMAs pegadas no gastan el patrón.

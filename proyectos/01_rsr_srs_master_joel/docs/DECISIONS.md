# DECISIONS — Decisiones técnicas y autorizaciones

## D-001 (2026-10-17) Agent Teams no está habilitado
- En esta sesión (app de escritorio Claude, pestaña Code) no existe la herramienta de creación de
  equipos (TeamCreate) ni la variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.
  `~/.claude/settings.json` no existe. La CLI `claude` no está en el PATH.
- Agent Teams es una función **experimental** de Claude Code CLI.
- Estado: pendiente de decisión del usuario (habilitar o usar alternativa).
- Actualización 2026-10-17: el usuario creó `~/.claude/settings.json` con
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` y `teammateMode: in-process`. CLI instalada
  (`~/.local/bin/claude.exe`, v2.1.302), pero esa carpeta **no está en el PATH**.
  En la sesión de la app de escritorio solo existe `SendMessage`; **no** existen TeamCreate,
  TaskCreate/TaskList/TaskUpdate ni el parámetro de compañero en el Agent tool → aquí no se
  pueden crear equipos. La verificación real debe hacerse desde la CLI.
- Verificación 2026-10-17 (sesión `proyecto-videos-b9`, app de escritorio, pestaña Code):
  - `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` activa en el proceso; settings aplicados.
  - Disponible: `Agent` (subagentes con nombre), `SendMessage`, `ListAgents`, `TaskStop`.
    `ListAgents` funciona y detecta la sesión par "RSR/SRS Trading AI con Agent Teams".
  - No disponible: `TeamCreate`, `TaskCreate`/`TaskList`/`TaskUpdate`. El parámetro
    `team_name` del Agent tool está obsoleto/ignorado (equipo implícito único).
  - Conclusión: soporte **parcial**. Mensajería entre agentes: sí. Equipos y tareas
    compartidas nativas: no. Alternativa viable: TL + subagentes con nombre coordinados por
    `SendMessage`, con `docs/TASKS.md` como tablero compartido.
  - Pendiente: verificar desde la CLI (`~/.local/bin/claude.exe`, fuera del PATH) si allí
    aparecen TeamCreate y las herramientas de tareas.

## D-002 (2026-10-17) Hallazgos del entorno
- Python 3.14.8 con `metatrader5 5.0.6231`, `numpy`, `pandas` ya instalados.
- GPU NVIDIA RTX 3050 8 GB → transcripción local con Whisper en GPU es viable.
- FFmpeg/ffprobe **no instalados**.
- Terminales MT5 instalados: FTMO, IC Markets Global, MetaTrader 5 Terminal, Weltrade.
  (BreakX, GainX, FX Vol, FlipX son índices sintéticos de Weltrade — por confirmar en el terminal.)

## D-003 (2026-10-17) Regla de cierre a 4 velas
- Propuesta del usuario, **no** atribuida a Master Joel.

## D-004 (2026-10-17) Instalación de herramientas audiovisuales (T05)
- Autorizada por el usuario el 2026-10-17. Análisis completo de videos **aún no autorizado**.
- Compatibilidad comprobada antes de instalar (`pip install --dry-run --only-binary :all:`):
  todas las dependencias tienen wheel binario para Python 3.14 (cp314/abi3).
- Entorno virtual: `.venv\` en la raíz del proyecto (Python 3.14.8). El Python global no se tocó.
- FFmpeg 9.0.2 full_build (winget `Gyan.FFmpeg`), incluye ffprobe y aceleración `cuda`.
  La ruta se añade al PATH de usuario; las consolas abiertas antes deben reiniciarse.
- Paquetes en `.venv`: faster-whisper 1.2.1, ctranslate2 4.8.3, onnxruntime 1.31.0,
  **av 18.1.0** (fijado `<19`: av 19.0.1 eliminó `metadata_errors`, que faster-whisper 1.2.1 usa →
  `TypeError`), nvidia-cublas-cu12 12.9.2.10, nvidia-cudnn-cu12 9.27.0.42. `pip check`: sin conflictos.
- GPU: ctranslate2 necesita `cublas64_12.dll`/cuDNN 9. Para usar `device="cuda"` hay que anteponer
  al PATH `.venv\Lib\site-packages\nvidia\{cublas,cudnn,cuda_nvrtc}\bin`. Driver NVIDIA 576.52.
- Verificación: audio sintético en español (voz TTS de Windows, fuera del proyecto), modelo `small`:
  - cuda/float16 y cpu/int8 → transcripción correcta con marcas de tiempo.
  - ffprobe sobre `2.- PATRON RSR Y SRS (importante)\1 - RSR Y SRS.mp4` (solo lectura): h264 1920x888
    50 fps, aac 44.1 kHz, 123.72 s. Fecha de modificación del video sin cambios.
- Modelos Whisper en caché en `~\.cache\huggingface\hub` (sin symlinks en Windows; ocupa algo más).

## D-005 (2026-10-17) Análisis de los 37 videos: organización y reanudación
- Autorizado por el usuario el 2026-10-17: transcripción con large-v3 (GPU), fotogramas y
  reconstrucción de reglas. **No** autorizado aún: programar la estrategia ni conectar MT5.
- IDs estables (`tools/videos.py`): `E2-01..08` (estrategia 2), `RSR-01..03`,
  `C0907-P01..P16` (clase 9 julio), `C1306-P01..P10` (clase 13 junio). Orden de las partes
  **numérico** (PARTE 2 antes que PARTE 10).
- Etapa 1 (`tools/transcribe.py`): large-v3, cuda/float16, `language=es`, VAD activado,
  `condition_on_previous_text=False` (reduce bucles/alucinaciones), sin `initial_prompt` para no
  sesgar el texto con términos que quizá no se digan. Salida `analysis/transcripts/<ID>.{json,md}`.
  Transcripción automática: puede tener errores en términos técnicos; toda cita se contrasta con
  el fotograma o se marca como dudosa.
- Etapa 2 (`tools/frames.py`): fotogramas por palabra clave dicha (+2 s), por cambio visual y
  como mínimo cada 20 s. Las palabras clave sirven solo para **buscar** momentos, no son reglas.
  Salida `analysis/frames/<ID>/` con `index.md` (tiempo, motivo, frase dicha).
- Etapa 3: análisis visual + verbal por agentes → `analysis/notes/<ID>.md` (fichas por video) →
  `docs/VIDEO_ANALYSIS.md` y `docs/STRATEGY_RULES.md` con cita `ID @ mm:ss` en cada conclusión.
- Reanudación: cada script salta lo que ya tiene su `.json`/`index.json`; cada ficha en
  `analysis/notes/` marca su estado. Relanzar el mismo comando continúa donde se quedó.
- Agentes: TL coordina y ejecuta los scripts. A1 (audiovisual) y A2 (estrategia) trabajan en las
  etapas 2-3; A6 (validación) revisa las citas. A3 (Python), A4 (MT5) y A5 (backtest) **no** se
  lanzan: su trabajo (programar/MT5) no está autorizado en esta fase.
- Soporte de Agent Teams parcial (D-001): subagentes con `Agent` + `SendMessage`, tablero en
  `docs/TASKS.md`. Máximo 2 agentes simultáneos.

## D-006 (2026-10-17) Resultados de las etapas 1-3 y decisiones de consolidación
- 37/37 transcripciones (large-v3), 1.951 fotogramas automáticos + ~300 extra a petición
  (`tools/extract_at.py`; corregido el 2026-10-17 un fallo que sobrescribía fotogramas del mismo
  segundo — solo afectó a E2-08 @00:57-00:59, re-extraídos). 37 fichas en `analysis/notes/`.
- Clases: C1306 P01→P10 y C0907 P01→P16 continuas, sin huecos. Orden cronológico 13 junio →
  9 julio confirmado por fechas en pantalla.
- Terminología: "piso", "techo", "PTP", "TPT" **no aparecen** en las 37 transcripciones
  (verificado por A6 con variantes). Master Joel usa SRS (compra) y RSR (venta)
  (E2-07 @00:47-00:54, escrito en pantalla). La equivalencia PTP=SRS, TPT=RSR es del usuario.
- Validación A6 (`docs/VALIDATION.md`): correcciones aprobadas en bloque por el TL.
  - El tramo C0907-P12 @00:27 → P16 @01:46 es la "estrategia número 3" (P12 @00:27-00:41,
    verificado por el TL). Sus citas se etiquetan, no se eliminan; las reglas que solo dependen de
    él (salida al 50 %) pasan a HIPÓTESIS para la estrategia 2. Pregunta al usuario (Q-11).
- **Aviso para el usuario**: PROJECT.md prevé 18 temporalidades desde M1, pero Master Joel dice
  "Esta estrategia es en M5, no es en temporalidades menores a M5. Puedes hacerla en M15, mucho
  mejor" (C1306-P02 @00:12-00:16, verificado por el TL). PROJECT.md no se modifica: decide el usuario.
- Salidas: Master Joel no usa SL ni TP y cierra a mano (1-2 velas de M5). El cierre a 4 velas
  sigue siendo regla del usuario (D-003); A6 confirmó que no se atribuye a Master Joel.

## D-007 (2026-10-17) Alcance: exclusivamente la estrategia RSR/SRS de Master Joel
Decisión del usuario.
- El software se desarrollará **solo** con RSR/SRS:
  - **SRS** (soporte–resistencia–soporte) = **compras**.
  - **RSR** (resistencia–soporte–resistencia) = **ventas**.
  - Coincide con lo que enseña Master Joel (STRATEGY_RULES R-04; E2-07 @00:47-00:54, escrito en
    pantalla). PTP/TPT quedan como nombres internos del usuario para SRS/RSR (D-006).
- **Excluidas por completo**: la estrategia número 3 (tramo C0907-P12 @00:27 → C0907-P16 @01:46)
  y cualquier otra estrategia independiente (estrategia 1 de EMAs / "1-2-3", "la oficial",
  Dash Pro, línea de seguridad, hedging/cobertura).
  → Resuelve Q-10 (sí, se excluyen) y Q-11 (las reglas que solo aparecen en ese tramo quedan fuera).
- **EMAs, indicadores y métodos adicionales**: no son condición de entrada salvo que se demuestre
  que forman parte indispensable de RSR/SRS tal como lo enseña Master Joel. Según los videos, las
  EMAs son de la estrategia 1 y combinarlas es opcional (C0907-P05 @00:26-00:43) → **excluidas**.
- La línea de tendencia y las ZTD (E2-03..E2-05) **no son indicadores**: son dibujos que enseña dentro
  del módulo de la estrategia 2, cuya entrada es el patrón SRS/RSR (E2-07). Se conservan como
  contexto de RSR/SRS; si la diagonal es obligatoria sigue abierto (Q-08).
- STRATEGY_RULES.md Rev. 2: el cuerpo del documento conserva solo lo que corresponde directamente a
  RSR/SRS. Lo excluido se mueve a un anexo de trazabilidad (mismos IDs, motivo y cita), sin valor
  normativo, para que ninguna regla desaparezca sin dejar rastro.
- La programación sigue **sin autorizar**. Pendientes: Q-01..Q-09.

## D-008 (2026-10-17) Sin filtro de tendencia obligatorio por ahora
Decisión del usuario.
- No se impone todavía un filtro obligatorio de tendencia: no está claro si RSR/SRS se usa solo a
  favor de la tendencia o también para detectar cambios de tendencia. Q-01 sigue abierta.
- Se encarga un informe específico (`docs/TREND_REPORT.md`, T12a): a favor / en contra /
  reversión-continuación, separando lo EXPLÍCITO de lo OBSERVADO en los ejemplos, con citas.
- Se deja planteada una futura comparación por backtesting de tres escenarios (solo a favor,
  solo en contra, sin filtro), **sin asumir** cuál será más rentable. No se ejecuta nada todavía.
- Resultado (Rev. 1, validada por A6 en `docs/TREND_VALIDATION.md`): enseña operar a favor de D1/H4,
  pero en clase también opera en contra y dice no mirar la tendencia; no hay definición objetiva de
  tendencia principal. Escenarios de backtest S-A (a favor), S-B (en contra), S-C (sin filtro).
  Antes de poder probarlos el usuario debe elegir la definición de tendencia (TREND_REPORT §6.2).

## D-009 (2026-10-18) Requisitos funcionales del escáner RSR/SRS
Decisión del usuario. Detalle en `docs/FUNCTIONAL_REQUIREMENTS.md` (FR-xx); son requisitos del
usuario, **no** enseñanzas de Master Joel, y no modifican STRATEGY_RULES.
- **Alcance**: se mantiene D-007 (solo RSR/SRS; SRS = compra, RSR = venta).
- **Símbolos**: los que publique el servidor MT5 conectado, con su nombre real; activar/desactivar y
  lotaje por símbolo desde la interfaz, guardable. Validar `volume_min`/`volume_max`/`volume_step` y
  que el símbolo sea operable; si el lote no es válido, informar y **no** abrir con otro volumen sin
  autorización. Ejemplos (no predeterminados): Break X600 0.80, FX Vol 20 0.01.
- **Temporalidades**: 18 seleccionables por símbolo (M1, M2, M3, M4, M5, M6, M10, M12, M15, M20, M30,
  H1, H2, H3, H4, H6, H8, H12). **Sin filtro obligatorio de TF superiores**: el patrón se evalúa en la
  TF donde se completa.
  - Se aparta de lo enseñado: "no es en temporalidades menores a M5" (R-02) y "los demás [pares] no
    los operen" (R-48). Las reglas se conservan como enseñanza; el software sigue al usuario.
  - Esto resuelve el aviso de D-006 sobre M1 y la pregunta Q-09.
- **Entrada**: solo tras el **cierre** de la vela que completa el patrón y con el patrón comprobado según
  STRATEGY_RULES; orden al primer precio disponible si la señal sigue vigente. Coincide con lo
  observado en su operación real (R-47) → resuelve Q-03. No se fija el nº de velas del patrón.
- **Salida (amplía D-003)**: cierre al finalizar la **4.ª vela posterior** a la de confirmación, en la
  misma TF, compras y ventas, con beneficio o pérdida; sin objetivo fijo de puntos.
  - Señal tardía: no se reinicia el conteo (0→4, 1→3, 2→2, 3→1, ≥4 caducada).
  - Registrar las horas de confirmación y de ejecución, las velas transcurridas y el resultado en
    puntos y en dinero, neto de costes.
  - Reinicios y desconexiones: propuesta en FUNCTIONAL_REQUIREMENTS §5.4.
- **Seguridad**: las 4 velas son la salida normal y no sustituyen las protecciones (por definir por el
  usuario, Q-05, futuro `docs/RISK_RULES.md`). Sigue sin autorizarse operar.
- **Tendencia**: FR-12 confirma D-008 en el software: no hay filtro obligatorio. Q-01 queda resuelta en
  ese sentido. Los escenarios S-A/S-B/S-C de TREND_REPORT pasan a ser un estudio opcional de backtest.
- Contradicciones abiertas K-02, K-03, K-05 y K-07 (FUNCTIONAL_REQUIREMENTS §8). Preguntas nuevas
  Q-12..Q-17 (STRATEGY_RULES §9).
- Ninguna decisión anterior se borra: D-003, D-006 y D-008 se amplían o resuelven aquí, con su motivo.

## D-010 (2026-10-18) Revisión de continuidad y requisitos complementarios
Origen: mensaje de continuidad del usuario (sesión remota de Claude), contrastado con los archivos.
- Verificado: 37 transcripciones (.md + .json), 37 fichas, STRATEGY_RULES Rev. 2.1, TREND_REPORT Rev. 1
  (Rev. 0 auditada en TREND_VALIDATION; correcciones aprobadas por el TL; la Rev. 1 no tiene segunda
  auditoría independiente), FUNCTIONAL_REQUIREMENTS Rev. 0 (D-009). Lo pedido en el mensaje ya estaba en
  D-009 salvo los añadidos de abajo. El mensaje cita cifras antiguas (59 reglas; ~2.325 fotogramas): las
  vigentes son 54 reglas en el cuerpo de Rev. 2 (+ Anexo A) y 1.951 fotogramas automáticos + ~300 extra.
- Añadidos a FUNCTIONAL_REQUIREMENTS (Rev. 1), sin cambiar requisitos previos: FR-08 (símbolo visible /
  seleccionado / habilitado), FR-09, FR-13 (TF sin datos → informar), FR-34 (motivo de salida), FR-35,
  FR-36, §7 backtesting (FR-50..FR-56), §7b casos de seguridad; ejemplo Flip X5 = 0.10.
- Telegram: el usuario recuerda que Master Joel opera el patrón en la TF observada. No hay ese material
  en el proyecto → recuerdo del usuario, no evidencia; no cambia STRATEGY_RULES.
- STRATEGY_RULES Rev. 2.2: nueva Q-18 (invalidación de un patrón en formación); Q-02 revisada con
  fotogramas de C0907-P10, sigue abierta.
- Sigue sin autorizarse programar, conectar MT5 de forma operativa u operar.

## D-011 (2026-10-18) Respuestas del usuario a Q-02, Q-06, Q-07, Q-12; T13 autorizada
Decisión del usuario.
- **Q-02** → configurable con las dos variantes (mecha que sobresale descalifica / no descalifica) para
  comparar en el backtest (FR-24). C-01b sigue abierta.
- **Q-07** → sin valores a ojo: el backtest mide varias opciones y el usuario elige con los resultados (FR-25).
- **Q-12** → el detector usa solo el patrón; cada señal registra si había ZTD en la misma TF (FR-14).
- **Q-06** → sin decidir. Primero se investiga vela a vela si R-49 (2 zonas) encaja con todos los
  ejemplos catalogados o si hay ejemplos reales de 3 zonas (A2 → `docs/PATTERN_STRUCTURE.md`).
- **T13** autorizada **solo lectura**: sin órdenes ni cambios en MT5. Hecha sobre el terminal Weltrade
  abierto (cuenta DEMO, hedging), con `tools/mt5_inspect.py` → `docs/MT5_API_NOTES.md`. No se usó
  `symbol_select` ni `order_*`.
- **CLAUDE.md**: SRS/RSR pasan a ser los nombres principales; PTP/TPT quedan como nombres del usuario.
- Resultado de Q-06 (`docs/PATTERN_STRUCTURE.md` Rev. 0, A2). El TL comprobó que los recuentos cuadran y
  la cita de T-37 en la transcripción.
  - Encajan con R-49 (2 niveles: el engaño rompe uno y la entrada cierra fuera del otro) **27 de los 30**
    ejemplos con estructura visible.
  - 3 zonas: solo **T-37** (C0907-P11 @ 00:52-01:20), y es ambiguo: puede ser una entrada alternativa.
  - Otra estructura: 2 (T-06, T-33). Indeterminables: 8.
  - La zona es de exactamente 2 velas en solo 6 casos; en 12 es un rango de más velas.
  - Opciones que quedan para el usuario: (A) R-49 con zona de 2 velas exactas o de un rango de ≥2;
    (B) 3 zonas; (C) ambas configurables. Q-06 sigue sin decidir.
- El detector sigue sin programarse.

## D-012 (2026-10-18) Q-06: estructura del patrón = R-49 (2 niveles)
Decisión del usuario, tomada a la vista de `docs/PATTERN_STRUCTURE.md`.
- Estructura principal del software: **opción A, R-49**. Una zona con nivel alto y nivel bajo; el engaño
  rompe uno de los dos; la entrada es la vela que cierra con cuerpo fuera del nivel opuesto. SRS = compra
  (el engaño rompe abajo y se entra al romper arriba); RSR = venta (al revés).
- R-49 queda marcada **"adoptada por decisión del usuario"**. **No** es una regla explícita de Master Joel:
  su clasificación sigue siendo HIPÓTESIS en STRATEGY_RULES.
- La estructura de **3 zonas no se programa** por ahora. T-37 (C0907-P11 @ 00:52-01:20) queda documentado
  como caso ambiguo.
- Configurable dentro de A, para el backtest:
  - **Zona**: por defecto un rango de **≥2 velas** (R-16, "mínimo dos velas"); variante "exactamente 2
    velas" para comparar.
  - **Niveles**: pueden salir de las mismas velas o de velas distintas (C0907-P04 @ 00:14-00:29,
    "prefiero… Pero está bien"); cada señal registra cuál fue el caso.
  - **Anchura máxima de la zona** ("pegadita" / "muy amplia", R-22): parámetro de Q-07, medido en el
    backtest (FR-25).
- Se encarga una auditoría corta de PATTERN_STRUCTURE.md a A6 sobre una muestra: T-37, T-06, T-33 y 7 al
  azar (T-22, D-A, T-34, T-08, T-28, T-35, T-29).
- Nada se borra: D-011 y la Rev. 0 de PATTERN_STRUCTURE se conservan. El detector sigue sin programarse.
- *Actualización (D-013)*: tras la auditoría, el recuento que respalda D-012 pasa de 27 a **29 de 30** ejemplos
  visibles que encajan con R-49. El "27 de los 30" de D-011 corresponde a la Rev. 0 y se mantiene como historial.

## D-013 (2026-10-18) Auditoría aplicada; Q-18, Q-08, Q-04; especificación del detector
Decisión del usuario.
- **Auditoría A6** (`docs/PATTERN_STRUCTURE_AUDIT.md`, muestra de 10): correcciones C-1..C-5 aplicadas →
  PATTERN_STRUCTURE Rev. 1.
  - R-49: 29 de 30.
  - 3 zonas: 1 (T-37, ambiguo).
  - Otra: 0.
  - Indeterminables: 8.
  STRATEGY_RULES se actualiza sin borrar el historial.
- **Q-18**: parámetros medidos en el backtest, con **tope obligatorio** para no esperar indefinidamente:
  - duración del engaño: base 1-2 velas (R-27), variantes 3 y 4;
  - anchura máxima de la zona: el parámetro de Q-07;
  - duración máxima total del patrón: varias opciones; si la supera, se descarta.
  Ninguno se presenta como regla de Master Joel.
- **Q-08**: la ZTD diagonal y el "primer toque" (R-13) solo se registran en cada señal; no filtran.
- **Q-04**: el backtest registra en paralelo las salidas de Master Joel (máx. 2 velas; cierre de vuelta en la
  zona) junto a la de 4 velas. FR-56 pasa de recomendado a obligatorio.
- **Q-05 y Q-13..Q-17**: se aplazan a la etapa de ejecución. No bloquean la especificación del detector.
- Se encarga `docs/DETECTOR_SPEC.md`: especificación en lenguaje sencillo, sin código, para que la revise el
  usuario. **No se programa nada.**

## D-014 (2026-10-18) Revisión de DETECTOR_SPEC (Rev. 1) y datos de prueba
Decisión del usuario.
- **Unidad de medida**:
  - P-2, F-2, F-3, F-5 y F-7 se expresan en múltiplos de la **vela media** (tamaño medio de las últimas N velas
    del mismo símbolo y TF, solo de velas anteriores). N es el parámetro P-7.
  - Es una escala de medida, **no** un indicador ni una condición de entrada.
- **S-5 → P-9**, con dos opciones. Por defecto: "al menos una vela que cierre dentro de la zona entre el engaño
  y la vela 0" (C1306-P03 @ 00:04-00:41; operación real 04:05/04:10).
- **P-6**: nueva variante (c). La mecha que sobresale por el lado de entrada no descalifica, pero eleva el
  nivel de entrada. Es una lectura de R-34 (C1306-P06 @ 00:17-00:27), no una regla explícita para este caso.
- **Detector causal**: sin velas futuras. Una zona da como máximo una señal; varios candidatos se vigilan en
  paralelo.
- **S-1 → P-8**: (a) todas las velas que quepan / (b) grupo más corto. **S-2, S-3, S-4 y S-7 aprobados.** S-6
  sigue abierto.
- **Datos de prueba**: se autoriza descargar en **solo lectura** el historial real de los casos con fecha
  visible. Se permite añadir el símbolo a Market Watch (`symbol_select`) y no se envían órdenes. Si el broker
  no tiene esas fechas, los casos se reconstruyen a mano.
  - Herramienta: `tools/mt5_history.py`.
  - Resultado en Weltrade-Demo, 2026-10-18:
    - El terminal entrega como máximo **100.000 velas por gráfico** ("Máx. barras en gráfico"): M1 desde
      ago 2026, M5 desde nov 2025, M15 y superiores desde 2023-2024.
    - **Las velas M5 de las clases (13 jun y 9 jul 2025) no son accesibles** con ese ajuste.
  - Descargado (`analysis/mt5/history/`):
    - FX Vol 20 M15, 20 ago → 10 sep 2025 (E2-07, E2-08);
    - FX Vol 20 H4, 15 ago → 25 sep 2025 (RSR-01);
    - FlipX 4 M15, 20 ago → 10 sep 2025 (E2-07, E2-08).
  - Comprobación preliminar: el rango del 24-25 ago (96.730-98.882) contiene los niveles leídos en E2-07
    (~97.100/97.350). Todavía no se ha cotejado vela a vela.
  - Los videos de las clases muestran **Weltrade-Real** y los datos son de **Weltrade-Demo**. Hay que comprobar
    que coinciden, por ejemplo con la vela 04:10 de FlipX 4 (O 78453, C 78472).
- Se añadió FlipX 4 a Market Watch (autorizado). No se envió ninguna orden. El detector sigue sin programarse.

## D-015 (2026-10-18) T14 autorizada solo para el detector; verificación Demo vs Real
Decisión del usuario.
- **T14 autorizada con límites**: programar **solo** el detector según DETECTOR_SPEC Rev. 1 y sus pruebas
  automáticas, usando el `.venv` del proyecto.
  - Datos de las pruebas: casos sintéticos, dibujos reconstruidos y los datos M15/H4 ya descargados.
  - **Prohibido**: backtest, conexión operativa a MT5 y envío de órdenes.
- "Máx. barras en gráfico": lo cambia **el usuario a mano** a Ilimitado y reinicia MT5. Cuando avise, se
  reintenta descargar M5 de jun/jul 2025 en solo lectura.
- Antes de usar esos datos se comprueba con la demo la vela 04:10 de FlipX 4 del 14-06-2025 (O 78453,
  C 78472). Si no coincide, los casos M5 se reconstruyen a mano.
- Resultado (2026-10-18): detector en `rsr_srs/`, pruebas en `tests/` (`unittest`, sin instalar nada).
  - 24 pruebas: 22 OK y 2 fallos (TC-04, TC-06).
  - Los fallos vienen de la definición de engaño de la especificación: la vela que vuelve y cierra dentro
    cuenta como engaño. La corrección S-9 está **pendiente** de la decisión del usuario.
  - F-7 no está implementado. Detalle en `docs/TEST_RESULTS.md`. Sin backtest, sin MT5 operativo, sin órdenes.
- Interpretación nueva usada en el código (S-8, a revisar): los niveles son "de las mismas velas" si las velas
  que fijan el máximo y el mínimo de la zona son la misma o contiguas.

## D-016 (2026-10-18) S-8 y S-9 aprobados; F-7 aplazado; datos M5 verificados
Decisión del usuario.
- **S-9 aprobado y aplicado** (`rsr_srs/detector.py`): después de la 1.ª vela del engaño, una vela que cierra
  dentro de la zona es "vuelta", aunque salga con mecha o apertura fuera.
  - Ejecutadas todas las pruebas: 25/25 OK.
  - Se corrigieron 3 pruebas con un error demostrado: TC-04 tenía las horas desplazadas, TC-10 tenía una vela
    de engaño que cerraba dentro y TC-09 contenía un patrón anidado. Detalle en TEST_RESULTS.
- **S-8 aprobado**: los niveles son "de las mismas velas" si las velas del máximo y del mínimo son la misma o
  contiguas.
- **F-7 aplazado**: se definirá junto con la "zona horizontal rota" de FR-14.
- **TC-11**: se documenta como comportamiento conocido (la zona absorbe la caída previa con anchura amplia y
  P-8 (a)), a medir en el backtest.
- **Datos M5**: el usuario puso "Máx. barras" en Ilimitado.
  - La vela 04:10 de FlipX 4 del 14-06-2025 **coincide** en la demo (O 78453, C 78472). También coinciden las
    de 04:05 (C 78451) y 04:50 (O 78651, H 78665, L 78608, C 78657).
  - Descargado M5 de 12-15 jun y 7-12 jul 2025 de FlipX 1-5, SFX Vol 20, FX Vol 20 y FX Vol 80
    (`analysis/mt5/history/`). Solo lectura, sin órdenes.
  - Con esos datos, el detector encuentra la compra real de C1306-P02 (vela 0 a las 04:10).
- **En curso**: el cotejo vela a vela de E2-07 y E2-08 con M15 (A1 → `docs/E2_CROSSCHECK.md`). Sin backtest
  ni órdenes.

## D-017 (2026-10-18) Ajustes del detector tras el cotejo E2; plan de validación sin sobreajuste
Decisión del usuario.
1. **P-4**: se añade la variante de **5 velas**, solo para el backtest. La base sigue siendo 1-2 (R-27).
2. **Elección de la zona** (aplicado en `rsr_srs/detector.py`; 27/27 pruebas OK):
   - con P-8 (a), la zona deja sitio para el engaño máximo: zona máxima = P-5 − P-4 − (2 con P-9 a, o 1);
   - si un candidato se descarta por duración total, se prueba la siguiente zona más corta. Esas zonas se
     siguen en silencio desde la vela del engaño, así que el detector sigue siendo causal;
   - cada reintento queda registrado (`Detector.retries`, `Signal.retried_from`) junto con el descarte que lo
     originó.
   - Pruebas nuevas: reserva para el engaño y reintento.
3. **Pruebas con datos reales**: comprueban la hora de la vela 0 **y** los niveles de la zona.
   - Tolerancia propuesta (pendiente de aprobación): cada nivel debe caer dentro del rectángulo que él dibujó,
     ampliado por el mayor de dos márgenes: el error de lectura del fotograma o 0,25 velas medias.
4. **S-10** (propuesta del usuario): varias zonas que confirman en la misma vela y dirección contarían como una
   sola señal. **No se aplica** hasta que el usuario responda a la opinión del TL.
5. **TC-10** se verifica con las velas M5 reales de C1306-P09 @ 00:00-00:21. No se ajustan datos para que una
   prueba pase.
6. **Falsos positivos**: en cada ventana de gráfico de los videos con datos reales se listan todas las señales
   del detector y se comparan con lo que Master Joel marcó, tomó o descartó.
7. **Sin sobreajuste**: los parámetros se eligen con una parte de los ejemplos y se comprueban con otra que no
   se usó para elegirlos.
8. Los casos de las clases de junio y julio con fecha visible se pasan a datos reales M5.
- En curso: A1 prepara `analysis/cases/windows.json` y `docs/CLASS_CROSSCHECK.md`. Sin backtest ni órdenes.
- **Resultado** (`docs/DETECTOR_VALIDATION.md`):
  - Datos y ventanas:
    - se descargaron en solo lectura los rangos con fecha visible que faltaban (FlipX 5 M5 del 10-06, FlipX 1
      y 4 M5 del 3-4 jul, etc.);
    - hay 54 ventanas con velas reales.
  - Elección de parámetros solo con E2: anchura 2 · engaño 5 · duración 24 · vela media 50 · all · inside ·
    mecha b. Son de esta comprobación; **no** son valores recomendados.
  - Resultados:

    | | E2 (elección) | Clases (comprobación) |
    |---|---|---|
    | Válidos acertados por hora | 7/7 | 12/14 |
    | … y además con su zona | 6/7 | 6/14 |
    | Descartes suyos que el detector señala | — | 5/9 |

  - Falsos positivos: unas 974 señales agrupadas en 9.671 velas (una cada 10 velas); 950 no coinciden con
    ninguna marca suya.
  - TC-10 con velas reales: T-29 tiene 4 velas de engaño. P-4 = 2 y 3 lo descartan; 4 y 5 lo encuentran.
  - Pruebas: 30/30 OK (nuevas: casos E2 por hora y zona, operaciones reales T-18 y T-23, y TC-10 real).

## D-018 (2026-10-18) Tolerancia de zona, S-10 y medición de filtros
Decisión del usuario.
- **Tolerancia de zona aprobada**: el nivel tiene que caer dentro de su rectángulo, ampliado por el mayor de
  dos márgenes: el error de lectura o 0,25 velas medias.
- **S-10 aprobado y aplicado**:
  - misma vela 0 y dirección = **una sola señal y una sola operación**;
  - `Signal.zones` guarda todas las zonas que la respaldan, con sus medidas.
  - 30/30 pruebas OK. Se adaptaron 2 pruebas que solo miraban la primera zona (TC-09 y el caso real T-13):
    ahora miran todas las zonas; no se cambió ningún dato.
- **Filtros medidos** (F-1…F-6 y anchura) con la separación curso/clases; no se eligieron valores finales
  (`docs/DETECTOR_VALIDATION.md` §6).
  - Ningún filtro separa bien: los que quitan muchas señales pierden válidos suyos.
  - F-5 tal como está medido no sirve.
  - Mejor pareja elegida con el curso: F-3 ≤ 1,0 + F-4 ≤ 0,4. En las clases quita el 9 %, pierde 0 válidos y
    elimina 0 descartes.
  - Quedan ~16-31 señales al día por símbolo en M5, ~7-11 en M15 y ~62-66 en M2.
- **ZTD horizontal**: definición propuesta en lenguaje sencillo en DETECTOR_SPEC §9. **Pendiente de
  aprobación; sin programar.** Sigue sin ser obligatoria (D-011).
- Pocos ejemplos etiquetados (~21 válidos): solo filtros sueltos y parejas; sin backtest ni órdenes.

## D-019 (2026-10-18) ZTD horizontal aprobada con ajustes; F-5 redefinido
Decisión del usuario sobre DETECTOR_SPEC §9.
- **Ajustes**:
  - la zona previa es distinta de la del patrón: termina antes de que el patrón empiece;
  - el sentido es explícito. En una compra, es una zona que frenó el precio por arriba, se rompió hacia arriba
    (cierre por encima) y se retesteó desde arriba, y el patrón se forma en ese retesteo. En una venta, el
    espejo.
- **Variante informativa en TF mayor** (H1 y H4): solo una columna más en la tabla. No es obligatoria ni filtra
  por defecto (D-009 sigue vigente).
  - Se descargaron en solo lectura H1 y H4 de 10 símbolos (25 may–16 jun, 20 jun–13 jul y 28 jul–11 sep 2025).
- **F-5 redefinido** con la misma idea de zona: distancia desde el cierre de la vela 0 hasta la **zona previa
  intacta** más cercana por delante. En una compra, es una zona que frenó el precio por arriba, está por encima
  del cierre y nadie la ha cerrado por encima. Sustituye a "cualquier máximo anterior" (R-37, R-45).
- **Programado**:
  - `rsr_srs/ztd.py`; registro por zona en `Signal.zones[i]["ztd_horizontal"]` y `Signal.context`;
  - filtro opcional `require_ztd` (desactivado por defecto);
  - pruebas en `tests/test_ztd.py`, 9 pruebas; total 39/39 OK.
  - Se corrigió una prueba negativa propia que pasaba sin comprobar nada (no había señal).
- **Medición** (`tools/measure_ztd.py`): con la misma separación curso/clases y sin elegir valores finales.
  Resultados en `docs/DETECTOR_VALIDATION.md` §7.
- Sin backtest ni órdenes.

## D-020 (2026-10-18) Fin de las combinaciones de filtros; plan de backtest (T15)
Decisión del usuario.
- **No se hacen más combinaciones de filtros**: con ~21 ejemplos etiquetados el riesgo de sobreajuste es alto.
- **Descripción oficial de los símbolos** (leída en solo lectura en MT5): índices sintéticos, por ejemplo
  FlipX "50% to change a direction…", FX Vol "fixed volatility", SFX "spikes…", BreakX "Reverse on jump level
  crossing…". Detalle en BACKTEST_PLAN §0.
- **T15 autorizada solo como backtest histórico** (sin conexión operativa, sin órdenes, sin cuenta real), con
  el plan fijado antes de ver resultados:
  - variantes: (a) sin filtros, (b) ZTD H4, (c) F-3 ≤ 1,0 + F-4 ≤ 0,4, (d) control aleatorio;
  - salida: 4.ª vela y, en paralelo, las salidas de Master Joel;
  - entrada a la apertura de la vela siguiente, con spread, comisión y deslizamiento;
  - el último 30 % de los datos se evalúa una sola vez;
  - 9 símbolos, M1, M5 y M15;
  - métricas de FR-53 y comparación con el control.
- Plan escrito en `docs/BACKTEST_PLAN.md`.
  - Deslizamiento propuesto: 0,5 × spread, con sensibilidad a 0 × y 1 ×.
  - Comisión: 0, según el historial de la cuenta.
  - Reserva: del 04-04-2026 al 17-10-2026.
  - Criterio: expectativa > 0 y mejor que el control con p < 0,05 corregido por Holm (9 comparaciones).
  - **No se ejecuta hasta que el usuario lo apruebe.**

## D-021 (2026-10-18) BACKTEST_PLAN aprobado con añadidos; ejecución
Decisión del usuario.
- **Añadidos escritos en BACKTEST_PLAN §8 antes de ejecutar**:
  1. solapamiento: (A) todas las señales y (B) cuenta con 1 operación abierta por símbolo y TF; el drawdown y
     el Monte Carlo salen de (B); el control sigue la misma regla;
  2. spread prudente si el del historial es claramente menor;
  3. la comisión hay que verificarla en la cuenta real;
  4. regla de decisión: si nada supera al control, "sin ventaja demostrada" y no se toca el detector para
     volver a usar esa reserva; si algo lo supera, se confirma con datos nuevos.
  - Detalles técnicos fijados también antes: unidad común en velas medias; sin medidas de contexto en el
    backtest; swap.
- **Spread (§8.2)**: FlipX 1-5 igual a la especificación; FX Vol 20 al 88 %; FX Vol 80 mayor. En **SFX Vol 20**
  (77 %) y **BreakX 600** (50 %, con velas a 0) se usa el mayor de los dos.
- **Datos descargados en solo lectura**: M1, M5 y M15 desde el 01-12-2024 y H4 desde el 01-06-2024 hasta el
  18-10-2026, de los 9 símbolos. Sin órdenes.
- **Código**:
  - `tools/backtest.py`;
  - pruebas de cálculo en `tests/test_backtest.py`; total 47/47 OK;
  - el detector tiene la opción `measure_context=False`; S-10 ya no recorre todas las señales anteriores;
  - `ztd.broken_zones` separa los pasos 1-4 sin cambiar la definición.

## D-022 (2026-10-18) Resultado del backtest (T15): sin ventaja demostrada
Decisión: aplicación de la regla fijada en D-021 (§8.4 del plan).
- **Ejecución**:
  - desarrollo (02-01-2025 → 03-04-2026) para comprobar que funciona;
  - reserva (04-04-2026 → 17-10-2026) **una sola vez**, sin cambiar nada tras ver desarrollo.
  - Para la memoria: como mucho 3 procesos y M1 de uno en uno, con resultados por símbolo+TF; las cifras no
    cambian.
  - Resultados: `analysis/backtest/dev.json` y `holdout.json`.
- **Reserva**: ninguna de las 9 pruebas (3 variantes × 3 TF) supera al control aleatorio tras costes.
  - p de Holm = 1,00 en todas, tanto en (A) como en (B). En (B) Holm se calculó después, con el mismo método.
  - Las 9 tienen expectativa negativa: unas −0,23 velas medias en M1, −0,09 en M5 y −0,04 en M15, igual que
    el control.
- **Conclusión**: **sin ventaja demostrada**.
  - No se modifica el detector para volver a probar con esta reserva.
  - No se pasa a construir la ejecución con estas variantes.

## D-023 (2026-10-18) Cierre del proyecto
Decisión del usuario.
- Tras D-022 (sin ventaja demostrada) se cierra el proyecto. El informe final está en `docs/FINAL_REPORT.md`.
- T16-T19 no se abordan. No hay conexión operativa ni órdenes.
- No se toca el código.

## Autorizaciones pendientes
- Programar la estrategia (T14 en adelante) y cualquier conexión operativa a MT5.


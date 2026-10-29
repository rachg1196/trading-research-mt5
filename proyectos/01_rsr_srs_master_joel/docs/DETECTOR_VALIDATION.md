# DETECTOR_VALIDATION — Señales del detector frente a lo que marcó Master Joel (D-017)

Fecha: 2026-10-18 · Script: `tools/evaluate_windows.py` → `analysis/cases/eval_results.json` · Ventanas y
marcas: `analysis/cases/windows.json` (A1; ver `docs/E2_CROSSCHECK.md` y `docs/CLASS_CROSSCHECK.md`).
**No es un backtest**: no simula entradas, salidas ni resultados. Solo cuenta señales. Sin MT5 operativo ni órdenes.

## 1. Qué se midió

- **54 ventanas de gráfico** de los videos con velas reales (Weltrade-Demo; desfase 0 y precios iguales a los
  de Weltrade-Real en las velas comprobadas). En total son **9.671 velas**, en M2, M5 y M15.
- **Marcas de Master Joel** en esas ventanas:

| Tipo de marca | Número | Cómo se cuenta |
|---|---|---|
| Patrón que tomó o dio por válido | 21 | positivo |
| Patrón que descartó | 11 | negativo |
| Patrón que señaló sin juzgar | 8 | se informa aparte |

- **Acierto por hora**: el detector da una señal en la misma dirección con la misma vela 0.
- **Acierto por zona**: además, el nivel alto y el nivel bajo caen dentro de los rectángulos que él dibujó, con
  la tolerancia propuesta (D-017): el mayor de dos márgenes, el error de lectura o 0,25 velas medias.
- **Señales agrupadas**: las que coinciden en vela 0 y dirección cuentan como una sola, como en la propuesta
  S-10. S-10 no se ha aplicado en el detector.
- Todos los filtros F-1…F-6 están **desactivados**: se mide el patrón solo.

## 2. Separación para no sobreajustar (punto 7)

- **Para elegir** los parámetros solo se usaron las ventanas del **curso grabado** (E2-07 y E2-08: FX Vol 20 y
  FlipX 4, agosto-septiembre de 2025). Son 8 ventanas con 7 patrones válidos y 2 descartes.
- **Para comprobar** se usaron las ventanas de las **dos clases en vivo** (13 de junio y 9 de julio de 2025:
  FlipX 1-5, SFX Vol, FX Vol 80 y otros). No intervinieron en la elección. Son 46 ventanas con 14 válidos o
  tomados y 9 descartes.
- Así, las comprobaciones se hacen con meses, símbolos y situaciones que el ajuste nunca vio.
- **Rejilla**: 768 combinaciones.

| Parámetro | Valores probados |
|---|---|
| Anchura máxima (P-2) | 1,5 · 2 · 3 · 4 |
| Engaño máximo (P-4) | 2 · 3 · 4 · 5 |
| Duración máxima (P-5) | 16 · 24 · 40 |
| Velas para la vela media (P-7) | 20 · 50 |
| Velas de la zona (P-8) | all · shortest |
| Vela dentro antes de la vela 0 (P-9) | inside · vela0 |
| Mecha del lado de entrada (P-6) | b · c |

- **Criterio de elección**, aplicado solo con E2: primero, más válidos acertados con su zona; después, más
  acertados por hora; después, menos descartes suyos señalados; por último, menos señales sin marcar.
- **Parámetros elegidos**: anchura 2 · engaño 5 · duración 24 · vela media de 50 · all · inside · mecha b.
  Son valores de esta comprobación, **no** recomendados (FR-25, FR-27).

| | Elección (E2) | Comprobación (clases) |
|---|---|---|
| Válidos o tomados acertados por hora | **7 / 7** | **12 / 14** |
| … y además con su zona | 6 / 7 | **6 / 14** |
| Descartes suyos que el detector sí señala | 0 / 2 | **5 / 9** |
| Señales agrupadas | 256 | 718 |
| … sin ninguna marca suya | 249 | 701 |

La referencia anterior (REF2: anchura 2 · engaño 2 · duración 16 · vela media de 20) da 6/7 y 8/14 por hora, y
3/7 y 1/14 por zona.

**En lenguaje sencillo**:
- Lo aprendido con el curso grabado **se mantiene bastante bien en las clases en cuanto a la hora**: el
  detector señala 12 de sus 14 patrones válidos.
- **No se mantiene en la zona**: solo en 6 de 14 usa la misma zona que él. A menudo acierta el momento con una
  zona algo distinta.
- **Separa mal lo que él descarta**: señala 5 de sus 9 descartes. Esos descartes se deben a motivos que el
  patrón solo no mide (vela larga, línea diagonal cercana, "no a mi gusto", mecha).

## 3. Falsos positivos (punto 6)

- Con los parámetros elegidos, el detector da **974 señales agrupadas en 9.671 velas**: aproximadamente **una
  cada 10 velas**.
- Master Joel marca **1-2 patrones por ventana**. **950 de las 974 señales no coinciden con ninguna marca
  suya.**
- Lo que se puede afirmar:
  - **Seguro**: de sus 11 descartes explícitos, el detector señala **5**:
    - T-26 (vela de ruptura larga);
    - AMPLIO (zona muy amplia);
    - M-04 ("no a mi gusto");
    - MECHA-P10 ("ya no califica");
    - T-37 (línea diagonal cercana).

    Esas 5 son señales que él **no habría tomado**.
  - **No se puede afirmar** que las 950 sin marca sean todas falsas. En cada ventana él comenta solo los
    patrones que le sirven para explicar; no revisa todas las velas.
  - Aun así, una señal cada 10 velas está muy lejos de "uno tiene que ser selectivo" (C0907-P10 @ 01:16). Lo
    razonable es pensar que **la mayoría no las habría tomado**.
- Detalle por ventana (señales, sin marca, aciertos): `analysis/cases/eval_results.json` → `chosen.per_window`.

Por qué hay tantas señales:
- **El patrón solo es muy frecuente**: dos niveles, una perforación y una vuelta ocurren constantemente en M5 y
  M15.
- **Él selecciona con lo que el patrón no mide**:
  - el contexto: la ZTD (zona horizontal rota y línea 1-2) y la tendencia, que FR-14 y FR-28 solo registran;
  - la calidad del patrón: zona "pegadita", vela no muy larga, obstáculo cerca, consolidación. Son los filtros
    F-1…F-6, que en esta medición están desactivados.
- **El siguiente paso lógico es medir cuánto reduce cada filtro y cada registro de contexto el número de
  señales sin perder sus válidos**, con la misma separación entre ejemplos de elección y de comprobación.

## 4. TC-10 con velas reales (punto 5)

- Con las velas reales de T-29 (C1306-P09, FlipX 5 M5, 10-06-2025) y la zona de sus 2 rectángulos de abajo,
  **el engaño tiene 4 velas** (15:05-15:20; vela 0 a las 15:30).
- Con P-4 = 2 y 3 el patrón se descarta; con 4 y 5 se encuentra con su zona.
  `test_real_data.test_tc10_con_velas_reales_t29` lo comprueba.
- La prueba sintética TC-10 (engaño de 3 velas) **no se modificó**. Sigue comprobando el mecanismo de P-4. Su
  descripción ya aclara que T-29 real tiene 4 velas.
- Con zonas formadas dentro del propio engaño, la vela de las 15:30 sale con cualquier P-4. Por eso hace falta
  comprobar la zona y no solo la hora.

## 5. Casos de las clases en M5 real (punto 8)

| Caso | Lo que hizo Master Joel | Detector (parámetros elegidos) |
|---|---|---|
| T-18 compra real FlipX 4, 14-06 04:10 | **tomó** | señal a las 04:10, zona como la suya |
| T-23 venta real FlipX 3, 14-06 05:35 | **tomó** | señal a las 05:35, zona distinta |
| T-19 | válido | hora sí, zona no |
| T-20 | válido | hora y zona |
| T-24 | válido | hora y zona |
| T-25 | válido | hora sí, zona no (su nivel bajo está en las mechas) |
| T-27 | válido | hora sí, zona no |
| T-28 | válido | hora y zona |
| T-29 | válido | hora y zona (necesita engaño ≥ 4) |
| T-30 | válido (mismo patrón que T-19) | hora sí, zona no |
| T-33 | válido (captura de un alumno) | hora sí, zona no |
| T-34 | válido (marcación corregida) | hora y zona |
| T-35 | válido | **no** (su nivel bajo es la línea de mechas, 101120) |
| M-07 | válido | **no** |
| T-26 | descartó: vela larga | **señala** (F-3 lo separaría: 1,15-1,21 frente a 0,04-0,76 en sus válidos) |
| AMPLIO (C1306-P05) | descartó: muy amplio | **señala** con estos parámetros (REF2, más estricto, no) |
| M-04 | descartó: "no a mi gusto" | **señala** |
| MECHA-P10 | descartó: "no califica" | **señala** (nada lo modela) |
| T-37 | descartó: línea diagonal cercana | **señala** (F-7 aplazado) |
| RECHAZO, M-02, M-09, T-21 | descartó | no señala |

Detalle vela a vela: `docs/CLASS_CROSSCHECK.md` (A1).

## 6. Medición de filtros (D-018) — sin elegir valores finales

Script: `tools/measure_filters.py` → `analysis/cases/filters_results.json`.
- **Base**: los parámetros de §2, sin filtros, con S-10 aplicado.
- **Cómo se aplica un filtro**: una señal se conserva si al menos una de sus zonas cumple el filtro.
- **Separación**: igual que en §2, curso (E2) y clases.
- **Antes de filtrar**: curso, 256 señales, 7/7 válidos y 0/2 descartes señalados; clases, 718 señales, 12/14
  válidos y 5/9 descartes señalados.

| Filtro (valor) | Curso: quita | Curso: válidos perdidos | Clases: quita | Clases: válidos perdidos | Clases: descartes eliminados |
|---|---|---|---|---|---|
| F-1 caída previa ≥ 0,5 | 2 % | 0 | 2 % | 0 | 0 |
| F-1 ≥ 1 | 10 % | 1 | 6 % | 0 | 0 |
| F-1 ≥ 2 | 20 % | 1 | 15 % | 0 | 0 |
| F-1 ≥ 3 | 36 % | 2 | 30 % | 0 | 0 |
| F-2 vela 0 ≤ 1 | 65 % | 6 | 68 % | 7 | 5 |
| F-2 ≤ 1,5 | 22 % | 3 | 20 % | 1 | 3 |
| F-2 ≤ 2 | 1 % | 0 | 5 % | 0 | 1 |
| F-3 cierre lejos ≤ 0,25 | 41 % | 4 | 49 % | 7 | 3 |
| F-3 ≤ 0,5 | 23 % | 4 | 19 % | 2 | 0 |
| F-3 ≤ 0,8 | 9 % | 1 | 6 % | 0 | 0 |
| F-3 ≤ 1,0 | 4 % | 0 | 3 % | 0 | 0 |
| F-4 rechazo ≤ 0,25 | 31 % | 1 | 20 % | 0 | 0 |
| F-4 ≤ 0,4 | 11 % | 0 | 7 % | 0 | 0 |
| F-4 ≤ 0,5 | 8 % | 0 | 3 % | 0 | 0 |
| F-5 espacio libre ≥ 0,5 | 69 % | 6 | 76 % | 12 | 5 |
| F-6 cruces ≤ 1 | 29 % | 4 | 30 % | 3 | 1 |
| F-6 ≤ 2 | 12 % | 3 | 13 % | 1 | 1 |
| F-6 ≤ 3 | 1 % | 1 | 7 % | 0 | 0 |
| P-2 anchura ≤ 1 | 58 % | 5 | 67 % | 9 | 3 |
| P-2 anchura ≤ 1,5 | 1 % | 1 | **−3 %** (da más señales) | 2 | 1 |

Unidades: F-1, F-2, F-3, F-5 y P-2 en velas medias; F-4 como fracción de la vela 0; F-6 en número de cruces.

**Lectura en lenguaje sencillo**:
- **Ningún filtro separa bien.** Los que quitan muchas señales (F-2 ≤ 1-1,5, F-3 ≤ 0,25-0,5, F-6 ≤ 1-2, anchura ≤ 1)
  quitan también patrones válidos suyos. Los que no pierden válidos quitan poco (2-15 %).
- **F-1 (caída previa)** es el más "limpio" en las clases: hasta ≥ 3 velas medias quita un 30 % y no pierde
  ningún válido. En el curso sí pierde 1-2. No elimina ninguno de sus descartes.
- **F-5 tal como está medido no sirve**: quita casi todo, válidos incluidos. Mide la distancia a cualquier
  máximo anterior, y en 50 velas casi siempre hay uno cerca. El "obstáculo" de Master Joel es una zona o una
  línea concreta, no cualquier máximo. Hay que redefinirlo (posiblemente con la ZTD, §7).
- **Anchura menor no siempre quita señales**: zonas más cortas dejan pasar otros patrones (−3 % con ≤ 1,5 en las
  clases).
- **Sus descartes** (vela larga, amplio, "no a mi gusto", mecha, diagonal) solo los quitan los filtros
  agresivos, que a la vez pierden válidos.

**Mejor combinación (elegida solo con el curso; máximo 2 filtros; condición: no perder ningún válido del
curso)**:
- Combinación: **F-3 ≤ 1,0 + F-4 ≤ 0,4**.
- Curso: quita el 15 % y pierde 0 válidos.
- Clases: quita el **9 %**, pierde **0** válidos y elimina **0** de sus descartes.

**Señales por día que quedarían** con esa combinación (`analysis/cases/signals_per_day.json`; índices
sintéticos 24 h; datos continuos descargados):

| TF | Señales/día por símbolo (rango) | Ejemplos |
|---|---|---|
| M2 | 62-66 | FlipX 4 (13-14 jun), FlipX 5 (7-8 jul) |
| M5 | 16-31 | FX Vol 20 25-29 · FX Vol 80 25-29 · FlipX 1-5 22-31 · SFX Vol 20 21 · SFX Vol 60 16-17 |
| M15 | 7-11 | FX Vol 20 8,7 · FlipX 4 8,8-8,9 · FlipX 1 6,8 · FlipX 5 11,0 |

**Conclusión**: con el patrón y estos filtros quedan **decenas de señales al día por símbolo en M5**. Master Joel
toma o marca muy pocas. La diferencia no la explican los filtros de calidad del patrón. Lo más probable es que
la explique el **contexto**, que en sus videos es donde busca el patrón: la ZTD. Siguiente medición: la ZTD
horizontal (§7), cuando el usuario apruebe la definición.

## 7. ZTD horizontal y F-5 redefinido (D-019) — sin elegir valores finales

Script: `tools/measure_ztd.py` → `analysis/cases/ztd_results.json`. Base y separación iguales que en §6.
- La base no lleva filtros: curso, 256 señales y 7/7 válidos; clases, 718 señales, 12/14 válidos y 5/9
  descartes señalados.
- Señales/día: mediana entre archivos continuos; en M5 se da mín.–mediana–máx.

| Filtro opcional | Curso: quita | Curso: válidos perdidos (de 7) | Clases: quita | Clases: válidos perdidos (de 12) | Clases: descartes eliminados (de 5) | Señales/día M5 | M15 | M2 |
|---|---|---|---|---|---|---|---|---|
| Sin filtro | — | — | — | — | — | 22–30–35 | 10,1 | 77,5 |
| ZTD-h misma TF (L 100, d 1) | 14 % | 1 | 20 % | 4 | 1 | 17–25–31 | 8,7 | 66,9 |
| ZTD-h misma TF (L 50, d 1) | 22 % | 2 | 24 % | 4 | 1 | 15–24–28 | 7,9 | 63,6 |
| ZTD-h misma TF (L 200, d 1) | 12 % | 1 | 16 % | 2 | 1 | 19–27–31 | 8,8 | 69,2 |
| ZTD-h misma TF (L 100, d 0,5) | 15 % | 2 | 22 % | 5 | 1 | 16–24–30 | 8,5 | 64,1 |
| ZTD-h misma TF (L 100, d 2) | 13 % | 1 | 18 % | 4 | 1 | 17–26–31 | 8,8 | 68,0 |
| ZTD-h misma TF + primer toque | 77 % | **7** | 81 % | **11** | 4 | 4–6–8 | 2,0 | 15,1 |
| **ZTD-h H1** (L 50, d 1) [informativa] | 20 % | 1 | 22 % | 3 | 1 | 9–23–27 | 8,1 | 64,1 |
| **ZTD-h H4** (L 50, d 1) [informativa] | 30 % | **0** | 32 % | **1** | 1 | 9–20–34 | 7,5 | 50,8 |
| F-5 nuevo: zona intacta ≥ 0,5 | 41 % | 3 | 49 % | 7 | 3 | 11–17–21 | 5,8 | 42,9 |
| F-5 nuevo ≥ 1 | 50 % | 4 | 61 % | 9 | 4 | 8–13–17 | 4,6 | 31,2 |
| F-5 nuevo ≥ 2 | 63 % | 5 | 68 % | 10 | 4 | 6–11–15 | 3,8 | 24,0 |
| F-5 nuevo ≥ 3 | 64 % | 5 | 69 % | 10 | 4 | 6–10–15 | 3,7 | 22,9 |

**Lectura en lenguaje sencillo**:
- **La ZTD horizontal en la misma TF casi no selecciona.** En M5/M15 hay zonas rotas y retesteadas
  constantemente, así que quita solo un 12-24 % y ya pierde 1-5 válidos.
- **Exigir además el "primer toque" lo rompe todo**: deja 4-8 señales al día en M5, pero pierde todos los
  válidos del curso y 11 de 12 en las clases. En la misma TF, sus patrones casi nunca están en el primer
  retesteo.
- **La ZTD en H4 es la que mejor se comporta**: quita alrededor de un tercio de las señales, no pierde ningún
  válido del curso, solo 1 de 12 en las clases, y elimina 1 descarte. Coincide con lo que enseña: la ZTD se
  marca en H4/D1 (R-01, R-12). Es **informativa**: según D-009 no filtra y no es obligatoria. Aun así quedan
  ~20 señales al día en M5.
- **El F-5 redefinido sí actúa como esperaba**: quita muchas más señales, la mitad o dos tercios, y elimina 3-4
  de sus 5 descartes en las clases. Pero también pierde muchos válidos (3-5 en el curso, 7-10 en las clases).
  Master Joel entra a veces con una zona intacta bastante cerca.
- Ningún filtro llega por sí solo a la selectividad de Master Joel sin perder sus válidos. La medición
  siguiente, si se decide, sería **combinar H4 con otro filtro suave** (por ejemplo F-1 o F-4) con la misma
  separación. No se ha hecho: el usuario pidió no ajustar muchos parámetros a la vez.

Límites:
- La ZTD en TF mayor usa la vela media de H1/H4 (20 velas) y L = 50 velas de esa TF. Son valores de medición.
- La ZTD diagonal (línea 1-2) sigue sin definir.

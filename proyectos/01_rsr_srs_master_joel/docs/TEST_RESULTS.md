# TEST_RESULTS — Pruebas del detector (T14)

Fecha: 2026-10-18 · Código: `rsr_srs/detector.py` · Pruebas: `tests/test_detector.py`, `tests/test_real_data.py`
Comando: `.venv\Scripts\python.exe -m unittest discover -s tests -t . -v`

- **Ejecución 1** (Rev. 1 de la especificación): 24 pruebas, 22 OK, 2 fallan (TC-04 y TC-06; nota 1).
- **Ejecución 2** (S-8 y S-9 aprobados, D-016): **25 pruebas, 25 OK**. Detalle en §Ejecución 2. Se añade
  TC-04 con datos reales.
No es un backtest: no se simulan entradas ni salidas (D-015).

Los casos de los videos se **reconstruyeron** a partir de las descripciones vela a vela de PATTERN_STRUCTURE (y
de los precios conocidos de la operación real en TC-04). No son velas reales. Los valores de los parámetros son
de prueba y ninguno es una regla de Master Joel.

| Caso | Esperado | Obtenido |
|---|---|---|
| TC-01 dibujo SRS 2 velas (C1306-P03) | compra; también con "exactamente 2" | OK |
| TC-02/03 dibujo RSR (C0907-P03, RSR-01) | venta | OK |
| **TC-04 operación real FlipX 4 (C1306-P02)** | compra con vela 0 a las 04:10 | **FALLA**: sin señal |
| TC-05/08 venta con engaño de mecha | venta | OK |
| **TC-06/07 verde larga que cierra dentro (C1306-P08, E2-08)** | compra en la vela siguiente | **FALLA**: sin señal |
| TC-09 niveles de velas distintas (C0907-P04) | venta con P-3 permitido; nada con P-3 no permitido | OK |
| TC-10 engaño de 3 velas (C1306-P09) | descarte con P-4 = 2; compra con 3 y 4 | OK |
| TC-11 zona muy amplia (C1306-P05) | no se forma con tope estricto; señal con tope amplio | OK (corregido un error de la propia prueba) |
| TC-12 consolidación F-6 (E2-05) | 4 cruces; descarte con F-6 ≤ 2 | OK |
| TC-13 vela de ruptura larga F-2 (C1306-P06) | señal sin filtro; descarte con F-2 | OK |
| TC-14 obstáculo F-5 (C0907-P11) | descarte si el obstáculo está más cerca que el mínimo | OK |
| TC-15 rechazo F-4 (C0907-P11) | descarte con F-4 | OK |
| TC-16 alejado F-7 | — | **no implementado**: F-7 necesita el método de la zona rota (T15) |
| TC-17 sin caída previa F-1 (C1306-P03) | descarte con F-1 | OK |
| TC-18/19/19b mecha del lado de entrada (P-6 a/b/c) | a: descarte; b: confirma la vela de 120; c: confirma solo por encima de 121 | OK |
| TC-20 una sola vela cruza los dos niveles | sin señal | OK |
| P-9 sin vela dentro | (a) descarte; (b) señal | OK |
| TC-21 entra y no cierra fuera | sin señal | OK |
| TC-22/24 ruptura sin engaño (S-3) | sin compra | OK |
| TC-23 tope de duración total | descarte | OK |
| TC-25 causalidad (serie aleatoria) | lo detectado no cambia al añadir velas | OK |
| TC-26 una señal por zona; candidatos en paralelo | sin duplicados; ≥2 vigilados a la vez | OK |
| Invariantes (serie aleatoria) | toda señal cumple la estructura | OK |
| Datos reales M15/H4: causalidad e invariantes | OK | OK (FX Vol 20 M15: 29 señales; H4: 3; FlipX 4 M15: 27) |
| Informativo E2-07 (FX Vol 20 M15, 24 ago) | compra con zona ~97.100-97.350 | **no aparece** con estos parámetros; ver nota 2 |

## Nota 1 — Por qué fallan TC-04 y TC-06 (fallo de la especificación, no del código)

DETECTOR_SPEC Rev. 1 dice que es engaño **toda vela que sobrepasa el nivel del engaño**, con mecha o con cuerpo.
En la operación real (TC-04) y en C1306-P08 (TC-06), la vela que **vuelve** del engaño empieza por debajo de la
zona y cierra dentro. Por eso su mínimo queda fuera de la zona y el detector la cuenta como **otra vela de
engaño**:
- en TC-04, el engaño pasa de 2 a 3 velas, supera el tope P-4 = 2 y el patrón se descarta;
- en TC-06, esa vela "borra" la vela que cierra dentro, y P-9 (a) descarta el patrón.

**Propuesta (S-9, pendiente de aprobación)**: después de la primera vela del engaño, una vela que **cierra
dentro de la zona** cuenta como vela de vuelta ("dentro") aunque su mecha o su apertura estén fuera. Seguirían
siendo engaño las que cierran fuera, por el lado del engaño. No lo he aplicado.

## Nota 2 — Comparación con E2-07

- Los niveles ~97.100/97.350 se leyeron a ojo en el fotograma.
- Los videos de las clases usan Weltrade-Real; el servidor de E2-07 no se ha comprobado. Los datos son de
  Weltrade-Demo.
- La hora del eje del gráfico no se ha cotejado.
- Hace falta cotejar vela a vela antes de concluir nada. En los datos sí aparecen ventas y compras cerca de esos
  días (p. ej. dos ventas el 24 ago a las 03:15 con zonas casi iguales: son candidatos paralelos de zonas
  solapadas, que se registran por separado; afecta a Q-16).

## Ejecución 2 (2026-10-18, D-016): S-9 aplicado

Se volvieron a ejecutar **todas** las pruebas.
- Con S-9, **TC-04 y TC-06 pasan**.
- Fallaron 3 pruebas que antes pasaban. Las tres eran errores **de la propia prueba**, que se demuestran así:

| Prueba | Por qué fallaba | Corrección |
|---|---|---|
| TC-04 (reconstruido) | Las horas estaban desplazadas una vela: la vela de cierre 78451 (la de las 04:05 en el video) estaba etiquetada como 04:10. Antes no se veía porque el caso fallaba antes de llegar a comprobarlo | La zona empieza a las 03:20; ahora la vela 0 es la de 78453 → 78472, a las 04:10 |
| TC-10 | La 3.ª vela "de engaño" cerraba **dentro** (105 > 104). Con S-9 esa vela es una vuelta, no engaño, así que la serie ya no tenía 3 velas de engaño | La 3.ª vela cierra fuera (102). Se sigue comprobando que P-4 = 2 descarta y 3 y 4 dan señal |
| TC-09 | La serie contiene **otro patrón válido** anidado: una zona de 3 velas cuyo engaño son la 4.ª vela y la de 99. Con S-9 también confirma, y la prueba contaba "1 señal con inicio Z0" sin distinguir la zona | La prueba comprueba la zona concreta de 4 velas (distintas → señal; P-3 no permitido → sin señal) |

- Resultado final: **25/25 OK**.
- La prueba nueva es **TC-04 con datos reales**: velas M5 de FlipX 4 descargadas de Weltrade-Demo, que
  coinciden con la ventana de datos del video (Weltrade-Real) en las velas de 04:05, 04:10 y 04:50.
  - El detector da la **compra con vela 0 a las 04:10 del 14-06-2025** con muchas combinaciones de parámetros.
  - Ejemplo: anchura 3, engaño 2-5, duración total 20-30.
  - Zona detectada: 78267/78341 – 78466. La zona de su dibujo llega a ~78456; la diferencia es una mecha.

## TC-11: comportamiento conocido (D-016)

Con una anchura máxima amplia y P-8 (a) "todas las que quepan", la ventana de la zona sigue hacia atrás y
**se traga la caída previa**:
- el nivel alto sube hasta el origen de la caída;
- el patrón deja de existir, porque la ruptura tendría que cerrar por encima de ese máximo lejano.

Con anchura 4 la zona abarca justo las 2 velas; con anchura 50 desaparece. No es un error: es el efecto
combinado de P-2 y P-8, y **hay que medirlo en el backtest**. Puede convenir combinar una anchura alta con
P-8 (b), o fijar un tope de anchura que no alcance la caída.

## F-7

Aplazado (D-016). Se definirá junto con la "zona horizontal rota" de FR-14.

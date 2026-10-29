# FINAL_REPORT — Informe final del proyecto RSR/SRS Trading AI

Fecha: 2026-10-18 · Estado: **proyecto cerrado** (D-023) · Conclusión: **sin ventaja demostrada** (D-022)

## 1. Objetivo
Comprobar si la estrategia SRS (compra) / RSR (venta) de Master Joel se puede convertir en reglas objetivas
y si esas reglas ganan dinero de forma sistemática, antes de construir un programa en Python que opere en
MetaTrader 5.

## 2. Qué se hizo
1. **Análisis de los 37 videos** (solo lectura, sin tocar los originales):
   - transcripción con marcas de tiempo (37/37);
   - 1.951 fotogramas extraídos;
   - una ficha visual y verbal por video (`analysis/notes/`);
   - las 2 clases en vivo reconstruidas en orden de PARTE, sin huecos.
2. **Reglas** (`docs/STRATEGY_RULES.md`):
   - 59 reglas con su cita (video + tiempo), clasificadas como explícita, observada, hipótesis,
     contradicción o duda;
   - contrastadas con los ejemplos (`docs/VALIDATION.md`), con 0 citas falsas y 0 conceptos ajenos;
   - la estructura de 2 niveles (R-49) encaja en 29 de 30 ejemplos y fue adoptada por el usuario (D-012).
3. **Detector** (`rsr_srs/`):
   - especificado en lenguaje sencillo (`docs/DETECTOR_SPEC.md`) y programado de forma causal, es decir,
     solo mira velas ya cerradas;
   - medidas F-1..F-6 y ZTD horizontal (D-019);
   - 47 pruebas automáticas, todas OK.
4. **Validación con los casos de los videos** (`docs/DETECTOR_VALIDATION.md`):
   - parámetros elegidos solo con el curso (E2) y comprobados con las clases;
   - en las clases encuentra a la hora correcta 12 de 14 patrones válidos, pero da muchas más señales que él
     (unas 1 de cada 10 velas);
   - ningún filtro separó bien los patrones válidos de los demás.
5. **Backtest** (`docs/BACKTEST_PLAN.md`, `tools/backtest.py`):
   - 9 símbolos, M1/M5/M15, de 02-01-2025 a 17-10-2026, con spread, deslizamiento y swap;
   - salida al cierre de la 4.ª vela (propuesta del usuario, no de Master Joel);
   - 3 variantes: (a) sin filtros, (b) ZTD en H4, (c) F-3 + F-4;
   - comparadas con un control que entra al azar (1.000 repeticiones);
   - el último 30 % (la reserva) se evaluó **una sola vez**, con la regla de decisión fijada antes.

## 3. Resultados (reserva, 04-04-2026 → 17-10-2026; D-022)
Las cifras son el resultado medio por operación en velas medias, después de costes. La probabilidad está
corregida por Holm (9 pruebas); por debajo de 0,05 habría ventaja.

**(A) Todas las señales**

| TF | Variante | Señales | Control | Prob. corregida |
|---|---|---|---|---|
| M1 | a | −0,227 | −0,225 | 1,00 |
| M1 | b | −0,227 | −0,223 | 1,00 |
| M1 | c | −0,221 | −0,223 | 1,00 |
| M5 | a | −0,088 | −0,093 | 1,00 |
| M5 | b | −0,085 | −0,092 | 1,00 |
| M5 | c | −0,088 | −0,092 | 1,00 |
| M15 | a | −0,041 | −0,052 | 1,00 |
| M15 | b | −0,044 | −0,052 | 1,00 |
| M15 | c | −0,046 | −0,052 | 1,00 |

**(B) Cuenta simulada (1 operación abierta a la vez por símbolo y TF)**

| TF | Variante | Señales | Control | Prob. corregida |
|---|---|---|---|---|
| M1 | a | −0,229 | −0,228 | 1,00 |
| M1 | b | −0,230 | −0,226 | 1,00 |
| M1 | c | −0,223 | −0,226 | 1,00 |
| M5 | a | −0,088 | −0,093 | 1,00 |
| M5 | b | −0,087 | −0,093 | 1,00 |
| M5 | c | −0,087 | −0,093 | 1,00 |
| M15 | a | −0,039 | −0,052 | 1,00 |
| M15 | b | −0,045 | −0,052 | 1,00 |
| M15 | c | −0,045 | −0,052 | 1,00 |

El periodo de desarrollo dio lo mismo: ninguna variante superó al control.

## 4. Conclusión
**Sin ventaja demostrada.**
- Operar las señales del detector da prácticamente lo mismo que entrar al azar, y en los dos casos se pierde
  por los costes.
- Cuanto menor es la temporalidad, más se pierde.
- Esto coincide con lo que dice el propio bróker de estos símbolos: son procesos sintéticos aleatorios.
- Por la regla fijada (D-021), el detector no se modifica para volver a probar con esta reserva.

## 5. Límites de la prueba
- **Lo que se probó es la lectura objetiva de la estrategia que hizo el proyecto**, no el criterio
  discrecional de Master Joel. El detector da muchas más señales que él y ningún filtro reprodujo su
  selección. Solo hay unos 21 ejemplos etiquetados, demasiado pocos para afinar sin sobreajustar.
- **Cierre a 4 velas**: es propuesta del usuario. Las salidas de Master Joel (2-3 velas y R-43) se midieron
  en paralelo, y la conclusión principal no se basa en ellas.
- **Alcance**: solo 9 símbolos sintéticos de Weltrade y 3 temporalidades (M1, M5, M15) de las 18 posibles.
- **Datos**: historial de la cuenta demo, en solo lectura. Que coinciden con la cuenta real se comprobó solo
  en algunas velas.
- **Costes**:
  - comisión supuesta 0, pendiente de verificar en la cuenta real; si existe, el resultado empeora;
  - deslizamiento supuesto (0,5 × spread; también se probaron 0 y 1);
  - spread prudente en SFX Vol 20 y BreakX 600.
- **Sin probar**: ZTD diagonal (sin definir) y F-7 (aplazado). La ZTD solo se probó horizontal y en H4.
- **Sin tamaño de lote ni gestión de riesgo** (Q-05, Q-13..Q-17 sin resolver). Los resultados son por
  operación y por lote, no la rentabilidad de una cuenta.

## 6. Herramientas reutilizables
- `rsr_srs/`: detector SRS/RSR causal, con parámetros configurables, ZTD horizontal y medidas F-1..F-6.
- `tests/`: 47 pruebas, con casos sintéticos y casos reales de los videos.
- `tools/backtest.py`: backtest con costes, cuenta simulada, control aleatorio, Holm y Monte Carlo;
  reanudable por símbolo y TF.
- `tools/mt5_inspect.py` y `tools/mt5_history.py`: inspección y descarga de historial de MT5 en solo
  lectura, sin órdenes.
- `tools/evaluate_windows.py`, `measure_filters.py` y `measure_ztd.py`: validación contra los casos de los
  videos.
- Herramientas de la transcripción y los fotogramas (por ejemplo, `tools/transcript_qc.py` y
  `tools/extract_at.py`).
- Material de análisis:
  - `analysis/notes/`, `analysis/frames/` y `analysis/cases/windows.json`;
  - el historial descargado en `analysis/mt5/history/`.

No se envió ninguna orden ni se usó conexión operativa a MT5 en todo el proyecto.

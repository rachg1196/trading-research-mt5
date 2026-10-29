# Lecciones aprendidas

1. **Antes de costes casi todo es azar; después de costes casi todo pierde.** En M1-M15 el spread es mayor que
   cualquier ventaja que tengan las reglas populares.
2. **Comparar contra el azar, no contra cero.** Una estrategia puede "ganar" solo porque el mercado subió en ese
   periodo; entradas al azar con la misma salida muestran cuánto aporta realmente la señal.
3. **Corregir por pruebas múltiples.** Con 17.882 pruebas, ~900 salen con p < 0,05 por suerte. Sin Holm se habrían
   "descubierto" cientos de estrategias falsas.
4. **Separar una reserva y usarla una sola vez.** Lo que se ve al diseñar ya está contaminado.
5. **Verificar los supuestos de ejecución.** En índices con saltos, una vela de 1 minuto no dice cómo se llena el
   stop. La regla que ganaba todos los meses con velas perdía con ticks reales (ver `img/velas_vs_ticks.png`).
6. **Lo discrecional no se puede probar.** Las reglas de los videos ("esto no me convence") se tradujeron a reglas
   objetivas; lo que se prueba es esa parte objetiva, y se documenta como límite.
7. **Las noticias programadas ya están en el precio.** En los eventos de Apple, el movimiento típico es "vender
   la noticia"; los resultados trimestrales no se diferencian de un día normal.

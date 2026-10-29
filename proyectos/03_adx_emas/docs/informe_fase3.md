# Fase 3 – Diagnóstico (informe)

Datos: desarrollo (ene-2025 a abr-2026). Reserva sin tocar.

## 1. Cómo se mueve BreakX 600 (minuto a minuto, 945.000 velas M1)
- 90,5% de los minutos el precio avanza exactamente ±300 puntos (deriva constante).
- La deriva mantiene su dirección en promedio 25 minutos (≈7.500 puntos). Solo cambia de dirección cuando hay un salto.
- 9,5% de los minutos hay un salto (break) de unos 2.880 puntos de media. El 95,5% de los saltos va EN CONTRA de la deriva. Ese es el "retroceso" que observabas.
- Después de un salto, la deriva sigue en la misma dirección el 58% de las veces y se invierte el 42%.
- La probabilidad de salto es la misma (9,5% por minuto) sin importar cuánto tiempo pasó desde el último: no se puede anticipar.
- Seguir la deriva da en promedio +0,7 ± 1,0 puntos por minuto, es decir, cero. Lo que se gana con la deriva se pierde en los saltos.
- La volatilidad es constante: rango mediano de vela M5 = 1.495 puntos todos los meses.
- Autocorrelación y variance ratio de M5 a H1 ≈ comportamiento aleatorio (VR 0,99-1,0).

Conclusión: el índice está diseñado como un juego equilibrado. No hay tendencia aprovechable con indicadores.

## 2. El acierto de la estrategia es exactamente el del azar
- En un mercado aleatorio, con SL 10.000, TP 5.000 y spread 130, la probabilidad de tocar el TP es (10.000 − 130) / 15.000 = 65,8%.
- Acierto de la estrategia en el backtest: 65,7%.
- Resultado esperado por operación = −spread: −130 pts hoy, −65 pts en 2025.

## 3. Por qué ganó esas 2 semanas
- Las 83 operaciones reales que coinciden con el backtest dieron +70.000 pts. Con un mercado aleatorio, eso ocurre ≈10% de las veces en un tramo dado.
- En 16 meses hay muchos tramos de 2 semanas; en el backtest el mejor dio +205.000 pts (may-2025). Rachas así son normales por azar.
- Ese mismo periodo, con el EA encendido todo el tiempo, dio −55.000 pts.
- El dinero se amplificó al subir el lote de 0,1 a 1,0 en esos días.

## 4. Por qué "dejó de funcionar"
- El mercado no cambió: misma volatilidad y misma estructura todos los meses.
- Lo único que cambió fue el spread: 65 → 130 desde dic-2025, lo que duplica la pérdida esperada.
- Las rachas negativas que vinieron después son la otra cara del mismo azar.

## 5. Cortes de la estrategia (horario, día, ADX, ATR, antigüedad de la tendencia, distancia a la EMA 30)
- Ningún grupo se separa del azar de forma confiable: el mejor de 24 horas tiene z = 2,0, que es lo esperable por casualidad al mirar 24 grupos.
- Elegir "las mejores horas" sería sobreajuste.

# Metodología

## 1. Datos
- Fuente: MetaTrader 5 (bróker Weltrade), API oficial `MetaTrader5` de Python, **solo lectura**.
- Se descarga solo M1; todas las demás temporalidades (M2…D1) se arman desde M1 y se verificó que coinciden
  100 % con las velas de MT5.
- Hora del servidor: Europe/Athens (UTC+2/+3), detectada por los huecos de M1.
- Historial útil por mercado: primer mes desde el cual ≥80 % de los días tienen ≥80 % de los minutos típicos.
- Acciones: ajuste de *splits* (salto de precio > 40 % entre velas seguidas, también en el spread).
- Índices sintéticos y la verificación final: ticks reales con bid y ask.

## 2. Costes
- Spread por vela con piso = máx(mediana del último año de desarrollo, mediana de las últimas ~7.000 velas).
- Swap según la especificación del símbolo (modo puntos / % anual / dinero por lote), con día triple.
- Comisión leída del historial de la cuenta (0 en este bróker).
- Resultado en USD por operación con el lote mínimo (`order_calc_profit`).

## 3. Simulación
- Señales solo con velas cerradas; entrada a la apertura de la vela siguiente (o en el primer minuto que toca
  una orden límite). Nada mira el futuro (se probó con un test causal).
- Stops con salto realista: si una vela abre más allá del stop, se llena a la apertura. Si en el mismo minuto se
  tocan stop y objetivo, cuenta el stop (conservador).
- Una operación abierta a la vez por estrategia/mercado/temporalidad/dirección.

## 4. Estadística
- **Control al azar:** 3.000 entradas en minutos aleatorios con la misma dirección, la misma salida y los mismos
  costes. La pregunta no es "¿gana?", sino "¿gana más que entrar al azar?".
- Test de Welch (aproximación normal) entre la estrategia y el control.
- **Corrección de Holm** sobre el contador global de pruebas (17.882): con miles de pruebas, decenas salen
  "significativas" por pura suerte.
- **Reserva:** el último 25 % del tiempo de cada mercado no se mira al diseñar. Se evalúa una sola vez.
- **Planes escritos antes de correr** cada prueba (`docs/planes/`), para no ajustar las reglas a los resultados.

## 5. Regla de decisión
Una prueba "pasa" solo si: ≥30 operaciones, neto por operación > 0, p de Holm < 0,05, mayoría de años positivos
y sigue positiva con el spread ×1,5.

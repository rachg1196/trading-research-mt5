# PROJECT — RSR/SRS Trading AI

Objetivo: estudiar los 37 videos de Master Joel, formalizar la estrategia RSR/SRS
(**SRS = compra, RSR = venta**; PTP/TPT son los nombres internos del usuario, D-006/D-007) y, solo
después, construir un programa Python para Windows que:
- se conecte a MT5 (varios brokers) con el paquete oficial `MetaTrader5`;
- liste los símbolos reales del servidor y permita activar/desactivar cada uno y fijar su lotaje
  (por BROKER+CUENTA+SÍMBOLO), validado contra `volume_min`/`volume_max`/`volume_step`;
- analice cada símbolo en las temporalidades que el usuario elija entre 18 (M1–H12), **sin filtro
  obligatorio de TF superiores**;
- genere señales solo con velas cerradas y entre tras el cierre de la vela que completa el patrón;
- cierre al finalizar la 4.ª vela posterior a la de confirmación (regla del usuario), sin reiniciar el
  conteo en señales tardías;
- haga backtesting y Monte Carlo, aplique controles de riesgo y tenga interfaz gráfica.

Requisitos funcionales del usuario: [FUNCTIONAL_REQUIREMENTS.md](FUNCTIONAL_REQUIREMENTS.md) (D-009).
Reglas de Master Joel: [STRATEGY_RULES.md](STRATEGY_RULES.md). Se mantienen separados.

Etapas: (1) videos → (2) STRATEGY_RULES.md verificado → (3) detector + tests →
(4) backtest/MC → (5) MT5, lotajes, cierres, GUI → (6) simulación, DEMO, auditoría →
(7) decisión del usuario sobre cuenta real.

Equipo: Team Lead + A1 Audiovisual, A2 Estrategia, A3 Python, A4 MT5, A5 Backtest/MC,
A6 Validación/Riesgo. Tablero en [TASKS.md](TASKS.md); decisiones en [DECISIONS.md](DECISIONS.md);
inventario en [VIDEO_INVENTORY.md](VIDEO_INVENTORY.md).

Cambios: 2026-10-18 (D-009) — SRS/RSR como nombres principales; símbolos, lotaje y TF por símbolo;
sin filtro de TF superiores; entrada tras cierre de vela; conteo de 4 velas y señales tardías.

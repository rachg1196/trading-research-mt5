# PLAN — Smart Money Concepts (motor LuxAlgo, igual que SMC_EA_LuxAlgo V2.4 de Raúl)

Fecha: 2026-10-28 · Raúl autorizó hacer todas las pruebas sin preguntar. Escrito ANTES de ver resultados.

## Motor (copiado de SMC_EA_LuxAlgo_V2.4.mq5 / LuxAlgo SMC)
- Pivotes internos (5 velas) y swing (50 velas) con la función "leg" de LuxAlgo.
- Ruptura alcista: cierre[i-1] <= nivel del pivote alto y cierre[i] > nivel (una vez por pivote). Bajista = espejo.
  CHoCH si la tendencia interna era contraria; BOS si era a favor.
- Order Block: en la ruptura, la vela entre el pivote y la ruptura con el mínimo más bajo (alcista) o el
  máximo más alto (bajista), con "parsed high/low" (velas de rango >= 2 ATR(200) se invierten). Mitigación High/Low.
- FVG LuxAlgo: low[i] > high[i-2], close[i-1] > high[i-2] y delta % de la vela central > umbral automático
  (2 × media acumulada). Bajista = espejo. Mitigación cuando el precio lo atraviesa.
- Solo velas cerradas; entrada a la apertura de la vela siguiente (o en el primer minuto que toca la zona).

## Señales (6)
1. RUPT_INT: toda ruptura interna (lo que operaba el EA de Raúl).
2. CHOCH_INT: solo CHoCH interno.  3. BOS_INT: solo BOS interno.
4. RUPT_SWING: ruptura de estructura swing (50).
5. OB_RETEST: el precio vuelve al Order Block interno antes de mitigarlo (máx. 100 velas) → orden límite en el borde.
6. FVG_RETEST: el precio vuelve al FVG antes de mitigarlo (máx. 100 velas) → orden límite en el borde.

## Filtro (2): sin filtro / solo a favor de la tendencia swing (último BOS/CHoCH de 50).
## Salida (2):
- X1 "Raúl": sin SL, TP = 2 × ATR(14), cierre al salir la señal contraria (ruptura interna opuesta), máx. 500 velas.
- X2 "fijo": SL = TP = 2 × ATR(14) (regla del Patron 123 EA), máx. 500 velas.
## Temporalidades (4): M1, M5, M15, H1. Direcciones: 2.
## Mercados
- Reales (decide): BTC, ETH, LTC, BCH, DASH, XRP, XAU, XAG, SPX → 6×2×2×4×2×9 = 1.728 pruebas. Holm global 16.154 + 1.728 = 17.882.
- Sintéticos Weltrade (informativo, familia propia): BreakX600, FlipX1-5, FXVol20, FXVol80, SFXVol20 → 1.728 pruebas.
Una operación abierta a la vez por señal/TF/dirección. Costes reales (spread, swap). Azar: 3000 entradas
al azar con la misma salida. Regla de decisión de siempre (≥30 ops, neto>0, Holm<0,05, mayoría de años +,
positiva con spread ×1,5). Solo desarrollo (75 %); reserva intacta.

## ADENDA (antes de mirar la reserva, 2026-10-28)
Unico candidato que paso en desarrollo con robustez (retraso 0-2 min, spread x2, 17/17 meses):
BreakX600 · M1 · RUPT_INT · sin filtro · X2 (SL=TP=2xATR14 SMA) · compras y ventas.
Reserva (2026-05-07 -> 2026-10-18) evaluada UNA vez, con el permiso general de Raul ("te doy permiso en todo").
Pasa si, en cada direccion: neto/op > 0, p < 0,05 (t de una cola, neto > 0) y mayoria de meses positivos.

## ADENDA 2 (2026-10-28, antes de mirar TrendX/SwitchX)
Regla FIJA (sin cambiar nada): M1 · ruptura interna · SL = TP = 2 x ATR(14) · compras y ventas, una a la vez por direccion.
Mercados nuevos (datos nunca usados con esta regla): TrendX 600/1200/1800, SwitchX 600/1200/1800, BreakX 1200/1800,
ene-2025 -> 29-oct-2026. Ademas BreakX 600 solo del 18 al 29-oct-2026 (datos nuevos).
Pasa cada mercado/direccion si: neto/op > 0, p (t de una cola) corregida por Holm (16 pruebas) < 0,05,
mayoria de meses positivos y positivo con spread x2.

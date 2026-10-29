"""ZTD horizontal y obstáculo (F-5) — DETECTOR_SPEC §9, aprobada con ajustes en D-019. Solo mide; no es
obligatoria (D-011) ni filtra por defecto.

Base: "rompe una zona, retestea" (E2-03 @ 00:13-00:37, R-11); patrón "en esa zona" (R-55); primer toque (R-13);
zonas alrededor donde el precio "puede rebotar" (R-37, R-45). Él marca la ZTD en H4/D1; aquí se mide en la misma
TF (Q-12) y, como columna informativa, en H1/H4 (D-019).

Todas las funciones son causales: reciben la lista de velas y solo miran índices anteriores a los indicados.
Distancias en velas medias (D-014).
"""
from datetime import datetime, timedelta

BUY = "SRS"   # igual que rsr_srs.detector.BUY (sin importar el detector, que usa este módulo)


def _prior_zone(candles, b, first, avg, max_width):
    """Zona previa más larga (>= 2 velas, con mechas, anchura <= max_width) que termina en la vela b."""
    hi, lo, best = float("-inf"), float("inf"), None
    for a in range(b, first - 1, -1):
        hi, lo = max(hi, candles[a].high), min(lo, candles[a].low)
        if (hi - lo) / avg > max_width:
            break
        if b - a >= 1:
            best = (a, hi, lo)
    return best


def broken_zones(candles, direction, zone_start, avg, lookback, max_width):
    """Pasos 1-4 de horizontal_ztd (no dependen del patrón, solo de dónde empieza): zonas previas que frenaron
    el precio, se rompieron antes de `zone_start` y siguen rotas. De la más reciente a la más antigua:
    (inicio, fin, alto, bajo, índice de la ruptura)."""
    buy = direction == BUY
    first = max(0, zone_start - lookback)
    out = []
    for b in range(zone_start - 3, first, -1):        # necesita b+1 (frena) y una ruptura antes del patrón
        pz = _prior_zone(candles, b, first, avg, max_width)
        if pz is None:
            continue
        a, hi, lo = pz
        if candles[b + 1].close > hi if buy else candles[b + 1].close < lo:
            continue                                   # no la frenó
        j = next((i for i in range(b + 2, zone_start)
                  if (candles[i].close > hi if buy else candles[i].close < lo)), None)
        if j is None:
            continue
        if any((candles[i].close < lo) if buy else (candles[i].close > hi) for i in range(j + 1, zone_start)):
            continue                                   # volvió a cerrar al otro lado: ya no está rota
        out.append((a, b, hi, lo, j))
    return out


def horizontal_ztd(candles, direction, zone_start, zone_low, zone_high, avg, lookback, dist, margin, max_width):
    """ZTD horizontal para un patrón cuya zona empieza en `zone_start` (índice en `candles`).

    Compra (venta = espejo):
      1. zona previa de >= 2 velas, distinta de la del patrón (termina antes de que empiece);
      2. la frenó por arriba: la vela siguiente a la zona previa no cierra por encima de su nivel alto;
      3. después, una vela la rompe hacia arriba (cierra por encima del nivel alto), antes del patrón;
      4. desde la ruptura hasta el patrón ninguna vela cierra por debajo de su nivel bajo (sigue rota);
      5. el patrón se forma en el retesteo desde arriba: su zona no queda por debajo de la zona previa y la
         distancia hasta su nivel alto es <= `dist` velas medias.
    Devuelve la más reciente que cumple, o None. `margin` (velas medias) define qué cuenta como "tocar" la zona
    rota al contar retesteos anteriores al patrón (primer toque, R-13).
    """
    buy = direction == BUY
    for a, b, hi, lo, j in broken_zones(candles, direction, zone_start, avg, lookback, max_width):
        if (zone_high < lo) if buy else (zone_low > hi):
            continue                                   # el patrón no está en un retesteo desde arriba/abajo
        gap = max(0.0, zone_low - hi) / avg if buy else max(0.0, lo - zone_high) / avg
        if gap > dist:
            continue
        touch = (lambda x: x.low <= hi + margin * avg) if buy else (lambda x: x.high >= lo - margin * avg)
        retests, prev = 0, False
        for i in range(j + 1, zone_start):
            t = touch(candles[i])
            retests, prev = retests + (t and not prev), t
        return {"start": a, "end": b, "high": hi, "low": lo, "break_index": j, "gap": gap,
                "bars_since_break": zone_start - j, "retests_before": retests, "primer_toque": retests == 0}
    return None


def obstacle_room(candles, direction, k, close0, avg, lookback, max_width):
    """F-5 redefinido (D-019): distancia, en velas medias, desde el cierre de la vela 0 hasta la zona previa
    intacta más cercana en la dirección de la operación (compra: una zona que frenó el precio por arriba, está
    por encima del cierre y ninguna vela la ha cerrado por encima hasta la vela 0). None si no hay ninguna.
    `k` es el índice de la vela 0; solo se miran velas anteriores."""
    buy = direction == BUY
    first = max(0, k - lookback)
    best = None
    for b in range(k - 2, first, -1):
        pz = _prior_zone(candles, b, first, avg, max_width)
        if pz is None:
            continue
        _, hi, lo = pz
        if candles[b + 1].close > hi if buy else candles[b + 1].close < lo:
            continue
        if buy and lo <= close0 or not buy and hi >= close0:
            continue                                   # no está por delante del precio
        if any((x.close > hi) if buy else (x.close < lo) for x in candles[b + 1:k + 1]):
            continue                                   # rota: ya no es obstáculo
        room = (lo - close0) / avg if buy else (close0 - hi) / avg
        best = room if best is None else min(best, room)
    return best


def htf_index(htf_candles, time, minutes):
    """Número de velas de la TF mayor ya CERRADAS en `time` ("YYYY-MM-DD HH:MM"); apertura + duración <= time."""
    t = datetime.strptime(time, "%Y-%m-%d %H:%M")
    n = 0
    for c in htf_candles:
        if datetime.strptime(c.time, "%Y-%m-%d %H:%M") + timedelta(minutes=minutes) <= t:
            n += 1
        else:
            break
    return n

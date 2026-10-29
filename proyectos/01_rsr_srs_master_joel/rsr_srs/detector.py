"""Detector SRS/RSR, vela a vela y causal (docs/DETECTOR_SPEC.md Rev. 1).

Estructura R-49 adoptada por el usuario (D-012): zona de >=2 velas con nivel alto y nivel bajo (con mechas);
engaño = velas que sobrepasan el nivel del engaño; vela 0 = primera que CIERRA más allá del nivel de entrada.
SRS (compra): engaño por debajo del nivel bajo, entrada al cerrar por encima del nivel alto. RSR al revés.

Todas las distancias van en "velas medias" (P-7): tamaño medio (máximo - mínimo) de las N velas cerradas
anteriores. Es una escala de medida, no un indicador ni una condición de entrada (D-014).
Ningún valor numérico de aquí es una regla de Master Joel: los fija quien llama, para medirlos en backtest.
No hay conexión a MT5 ni envío de órdenes (D-015).
"""
from dataclasses import dataclass, field

from .ztd import horizontal_ztd, obstacle_room

BUY, SELL = "SRS", "RSR"


@dataclass(frozen=True)
class Candle:
    time: object
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Params:
    max_width: float            # P-2 anchura máxima de la zona, en velas medias (tope obligatorio)
    max_total: int              # P-5 duración máxima total del patrón, en velas (tope obligatorio)
    avg_n: int                  # P-7 N velas para la vela media
    wick: str                   # P-6 mecha que sobresale por el lado de entrada: "a" descalifica,
                                #     "b" no descalifica, "c" eleva el nivel de entrada (lectura de R-34)
    zone_candles: str = "range"  # P-1 "range" (>=2) | "exact2"
    distinct_levels: bool = True  # P-3 niveles de velas distintas permitidos
    max_fake: int = 2            # P-4 velas máximas del engaño (base 1-2, R-27; variantes 3 y 4)
    zone_pick: str = "all"       # P-8 "all" (todas las que quepan) | "shortest" (2 velas)
    single_candle: str = "inside"  # P-9 "inside": al menos una vela que cierre dentro entre engaño y vela 0
                                   #     "vela0": solo se descarta si la vela 0 sobrepasa el nivel del engaño
    lookback: int | None = None  # velas de contexto para F-1 y F-5 (por defecto, avg_n)
    # Filtros F-n (None = desactivado; se miden siempre)
    f1_min_prior: float | None = None     # movimiento previo en contra, mínimo
    f2_max_vela0: float | None = None     # tamaño de la vela 0, máximo
    f3_max_dist: float | None = None      # distancia del cierre de la vela 0 al nivel de entrada, máximo
    f4_max_rejection: float | None = None  # mecha de rechazo de la vela 0 (fracción de su rango), máximo
    f5_min_room: float | None = None      # distancia a la zona intacta más cercana por delante, mínimo (D-019)
    f6_max_crossings: int | None = None   # cruces de la zona (consolidación), máximo
    require_ztd: bool = False             # filtro opcional: exigir ZTD horizontal en la misma TF (D-019)
    # ZTD horizontal y F-5 (D-019). Valores de medición, no recomendados.
    ztd_lookback: int = 100               # velas hacia atrás para buscar zonas previas
    ztd_dist: float = 1.0                 # distancia máxima patrón - zona rota, en velas medias
    ztd_margin: float = 0.5               # margen para contar un "toque" de la zona rota, en velas medias
    measure_context: bool = True          # False: no calcula ZTD ni F-5 (backtest, BACKTEST_PLAN §8); con
                                          # False, require_ztd y f5_min_room no se pueden usar

    def __post_init__(self):
        checks = [(self.wick in ("a", "b", "c"), "wick"), (self.zone_candles in ("range", "exact2"), "zone_candles"),
                  (self.zone_pick in ("all", "shortest"), "zone_pick"),
                  (self.single_candle in ("inside", "vela0"), "single_candle"),
                  (self.max_width > 0 and self.max_total >= 4 and self.avg_n >= 1 and self.max_fake >= 1, "topes")]
        checks.append((self.measure_context or not (self.require_ztd or self.f5_min_room is not None),
                       "measure_context"))
        bad = [name for ok, name in checks if not ok]
        if bad:
            raise ValueError(f"parámetros no válidos: {bad}")


@dataclass
class Signal:
    direction: str
    zone_start: int             # índices dentro de la serie recibida
    zone_end: int
    vela0_index: int
    vela0: Candle
    level_high: float           # niveles originales de la zona
    level_low: float
    entry_level: float          # nivel que tuvo que superar la vela 0 (puede subir con P-6 "c")
    levels: str                 # "mismas" | "distintas" (velas que fijan el máximo y el mínimo)
    fake_candles: int
    fake_depth: float           # en velas medias
    total_candles: int          # desde la primera vela de la zona hasta la vela 0, incluidas
    inside_candles: int         # velas que cerraron dentro de la zona entre engaño y vela 0
    avg_candle: float
    width: float                # anchura en velas medias
    wick_events: list = field(default_factory=list)  # índices de velas con mecha por el lado de entrada
    measures: dict = field(default_factory=dict)     # F-1..F-7
    context: dict = field(default_factory=dict)      # ZTD, primer toque, tendencia: solo registro (T15)
    retried_from: tuple | None = None                # zona descartada por duración de la que viene (D-017)
    zones: list = field(default_factory=list)        # S-10: todas las zonas que confirman en esta vela 0 y
                                                     # dirección (la 1.ª es la de los campos de arriba)


@dataclass
class Discard:
    direction: str
    zone_start: int
    zone_end: int
    at_index: int
    reason: str
    measures: dict = field(default_factory=dict)


class _Candidate:
    def __init__(self, direction, start, end, hi, lo, avg, levels, k):
        self.direction, self.start, self.end = direction, start, end
        self.hi, self.lo, self.avg, self.levels = hi, lo, avg, levels
        self.entry = hi if direction == BUY else lo     # nivel de entrada
        self.fake_count, self.fake_extreme = 0, None
        self.inside_since_fake = False
        self.inside_total = 0
        self.wick_events = []
        self.fake_start = k
        self.silent = False        # zona alternativa que se sigue sin registrar nada (D-017)
        self.shadows = []          # zonas más cortas, de la más larga a la más corta
        self.retry = False         # descartada por duración total: probar la siguiente zona
        self.retried_from = None   # zona (inicio, fin) de la que viene por reintento


class Detector:
    """Recibe velas cerradas de UN símbolo y UNA TF, en orden. Solo usa velas ya cerradas (causal)."""

    def __init__(self, params: Params):
        self.p = params
        self.candles: list[Candle] = []
        self.active: list[_Candidate] = []
        self.used_zones: set = set()    # una zona da como máximo una señal
        self.signals: list[Signal] = []
        self.discards: list[Discard] = []
        self.retries: list = []         # (vela, dirección, zona descartada, zona promovida)

    @property
    def history_ok(self):
        """FR-13: hay velas suficientes para medir (N para la vela media + 2 de zona + 1)."""
        return len(self.candles) > self.p.avg_n + 2

    def update(self, c: Candle):
        """Procesa una vela recién cerrada. Devuelve las señales y descartes producidos por ella."""
        self.candles.append(c)
        k = len(self.candles) - 1
        n_sig, n_dis = len(self.signals), len(self.discards)
        still = [x for x in (self._advance(cand, c, k) for cand in self.active) if x is not None]
        for direction in (BUY, SELL):
            cand = self._new_candidate(direction, k)
            if cand is not None:
                cand = self._advance(cand, c, k)
                if cand is not None:
                    still.append(cand)
        self.active = still
        return self.signals[n_sig:], self.discards[n_dis:]

    def _advance(self, cand, c, k):
        """Avanza un candidato y sus zonas alternativas. Devuelve el candidato vivo (quizá el promovido) o None."""
        if self._step(cand, c, k):
            cand.shadows = [s for s in cand.shadows if self._step(s, c, k)]
            return cand
        if not cand.retry:
            return None
        # Descartada por duración total: se prueba la siguiente zona más corta con esta misma vela.
        shadows = cand.shadows
        for i, nxt in enumerate(shadows):
            nxt.silent, nxt.retried_from = False, (cand.start, cand.end)
            self.retries.append((k, cand.direction, (cand.start, cand.end), (nxt.start, nxt.end)))
            if self._step(nxt, c, k):
                nxt.shadows = [s for s in shadows[i + 1:] if self._step(s, c, k)]
                return nxt
            if not nxt.retry:       # confirmó o se descartó por otro motivo (ya registrado)
                return None
            cand = nxt
        return None

    # --- formación de la zona (Paso 1) ---------------------------------------------------------------
    def _avg(self, k):
        n = self.p.avg_n
        if k < n:
            return None
        prev = self.candles[k - n:k]
        avg = sum(x.high - x.low for x in prev) / n
        return avg if avg > 0 else None

    def _new_candidate(self, direction, k):
        """Crea un candidato si la vela k empieza un engaño sobre una zona que termina en k-1."""
        if k < 2:
            return None
        avg = self._avg(k)
        if avg is None:
            return None
        p = self.p
        # D-017: la zona deja sitio para el engaño máximo (P-4) + (vela dentro, si P-9 a) + vela 0
        reserve = p.max_fake + (2 if p.single_candle == "inside" else 1)
        max_len = 2 if (p.zone_candles == "exact2" or p.zone_pick == "shortest") else p.max_total - reserve
        c = self.candles[k]
        options = []
        hi, lo = float("-inf"), float("inf")
        for length in range(1, min(max_len, k) + 1):
            x = self.candles[k - length]
            hi, lo = max(hi, x.high), min(lo, x.low)
            if (hi - lo) / avg > p.max_width:
                break
            if length >= 2:
                options.append((length, hi, lo))
        if not options:
            return None
        # La zona es la ventana elegida por P-8: la más larga que cabe, o la de 2 velas.
        length, hi, lo = options[-1]
        start, end = k - length, k - 1
        if (direction, start, end) in self.used_zones:
            return None
        if not (c.low < lo if direction == BUY else c.high > hi):   # la vela k no empieza un engaño
            return None
        levels = self._levels(start, end, hi, lo)
        if levels == "distintas" and not p.distinct_levels:
            return None
        cand = _Candidate(direction, start, end, hi, lo, avg, levels, k)
        # D-017: las ventanas más cortas se siguen en silencio desde esta misma vela; si la principal se descarta
        # por duración total, se promueve la siguiente (solo con velas ya cerradas: sigue siendo causal).
        for length, hi, lo in reversed(options[:-1]):
            s_start = k - length
            if (direction, s_start, end) in self.used_zones:
                continue
            levels = self._levels(s_start, end, hi, lo)
            if levels == "distintas" and not p.distinct_levels:
                continue
            shadow = _Candidate(direction, s_start, end, hi, lo, avg, levels, k)
            shadow.silent = True
            cand.shadows.append(shadow)
        return cand

    def _levels(self, start, end, hi, lo):
        """"mismas" si las velas que fijan el máximo y el mínimo son la misma o contiguas (interpretación S-8)."""
        zone = range(start, end + 1)
        i_hi = [i for i in zone if self.candles[i].high == hi]
        i_lo = [i for i in zone if self.candles[i].low == lo]
        return "mismas" if min(abs(a - b) for a in i_hi for b in i_lo) <= 1 else "distintas"

    # --- engaño, vuelta y ruptura (Pasos 2-5) -------------------------------------------------------
    def _step(self, cand, c, k):
        """Aplica la vela k al candidato (la que lo crea es siempre de engaño). Devuelve True si sigue vivo."""
        p, buy = self.p, cand.direction == BUY
        total = k - cand.start + 1
        beyond_fake = c.low < cand.lo if buy else c.high > cand.hi
        closes_out = c.close > cand.entry if buy else c.close < cand.entry
        if total > p.max_total:
            cand.retry = True
            return self._discard(cand, k, "duración total > P-5"
                                 + (" → se prueba la zona más corta" if cand.shadows else ""))
        if beyond_fake and closes_out:
            return self._discard(cand, k, "una sola vela cruza los dos niveles (R-28)")
        closes_inside = (cand.lo <= c.close <= cand.entry) if buy else (cand.entry <= c.close <= cand.hi)
        if beyond_fake and closes_inside and k != cand.fake_start:
            beyond_fake = False     # S-9: la vela que vuelve y cierra dentro no es engaño, aunque salga con mecha
        if closes_out:
            if p.single_candle == "inside" and not cand.inside_since_fake:
                return self._discard(cand, k, "sin vela que cierre dentro entre engaño y vela 0 (P-9 a)")
            return self._confirm(cand, c, k, total)
        if beyond_fake:
            cand.fake_count += 1
            ext = c.low if buy else c.high
            cand.fake_extreme = ext if cand.fake_extreme is None else (min if buy else max)(cand.fake_extreme, ext)
            cand.inside_since_fake = False
            if cand.fake_count > p.max_fake:
                return self._discard(cand, k, "engaño > P-4")
            return True
        if closes_inside:
            cand.inside_since_fake = True
            cand.inside_total += 1
        if c.high > cand.entry if buy else c.low < cand.entry:      # mecha por el lado de entrada (P-6)
            cand.wick_events.append(k)
            if p.wick == "a":
                return self._discard(cand, k, "mecha sobresale de la zona (P-6 a)")
            if p.wick == "c":
                cand.entry = c.high if buy else c.low
                if abs(cand.entry - (cand.lo if buy else cand.hi)) / cand.avg > p.max_width:
                    return self._discard(cand, k, "anchura > P-2 al elevar el nivel (P-6 c)")
        return True

    def _discard(self, cand, k, reason, measures=None):
        if cand.silent:
            return False
        self.discards.append(Discard(cand.direction, cand.start, cand.end, k, reason, measures or {}))
        self.used_zones.add((cand.direction, cand.start, cand.end))
        return False

    def _confirm(self, cand, c, k, total):
        if cand.silent:     # una zona alternativa que confirma mientras la principal sigue viva no cuenta
            return False
        buy, p, avg = cand.direction == BUY, self.p, cand.avg
        m = self._measures(cand, c, buy, k)
        ztd = horizontal_ztd(self.candles, cand.direction, cand.start, cand.lo, cand.hi, avg,
                             p.ztd_lookback, p.ztd_dist, p.ztd_margin, p.max_width) if p.measure_context else None
        failed = [name for name, bad in (
            ("F-1", p.f1_min_prior is not None and m["F1_prior_move"] < p.f1_min_prior),
            ("F-2", p.f2_max_vela0 is not None and m["F2_vela0_size"] > p.f2_max_vela0),
            ("F-3", p.f3_max_dist is not None and m["F3_close_dist"] > p.f3_max_dist),
            ("F-4", p.f4_max_rejection is not None and m["F4_rejection"] > p.f4_max_rejection),
            ("F-5", p.f5_min_room is not None and m["F5_room"] is not None and m["F5_room"] < p.f5_min_room),
            ("F-6", p.f6_max_crossings is not None and m["F6_crossings"] > p.f6_max_crossings),
            ("ZTD", p.require_ztd and ztd is None),
        ) if bad]
        if failed:
            return self._discard(cand, k, "filtro " + ", ".join(failed), m)
        self.used_zones.add((cand.direction, cand.start, cand.end))
        depth = abs((cand.fake_extreme if cand.fake_extreme is not None else cand.lo if buy else cand.hi)
                    - (cand.lo if buy else cand.hi)) / avg
        zone = {"start": cand.start, "end": cand.end, "high": cand.hi, "low": cand.lo, "entry": cand.entry,
                "levels": cand.levels,
                "fake_candles": cand.fake_count, "avg_candle": avg, "measures": m, "retried_from": cand.retried_from,
                "ztd_horizontal": ztd}       # dict de rsr_srs.ztd.horizontal_ztd o None (solo registro, D-019)
        context = {"ztd_horizontal": ztd is not None, "ztd_detail": ztd, "ztd_diagonal": None,
                   "primer_toque": None if ztd is None else ztd["primer_toque"], "tendencia": None}
        same = []           # las señales se añaden en orden de vela: solo hace falta mirar las del final
        for s in reversed(self.signals):
            if s.vela0_index != k:
                break
            if s.direction == cand.direction:
                same.append(s)
        if same:            # S-10 (D-018): misma vela 0 y dirección = una sola señal; se guardan todas las zonas
            same[0].zones.append(zone)
            return False
        self.signals.append(Signal(
            cand.direction, cand.start, cand.end, k, c, cand.hi, cand.lo, cand.entry, cand.levels,
            cand.fake_count, depth, total, cand.inside_total, avg, (cand.hi - cand.lo) / avg,
            list(cand.wick_events), m,
            context, cand.retried_from, [zone]))
        return False

    def _measures(self, cand, c, buy, k):
        """F-1..F-7, en velas medias salvo F-4 (fracción del rango de la vela 0) y F-6 (número de cruces).
        F-5 (D-019): distancia a la zona previa intacta más cercana por delante (rsr_srs.ztd.obstacle_room)."""
        avg = cand.avg
        lb = self.p.lookback or self.p.avg_n
        before = self.candles[max(0, cand.start - lb):cand.start]
        zone = self.candles[cand.start:cand.end + 1]
        if buy:
            prior = (max(x.high for x in before) - cand.lo) / avg if before else 0.0
            dist = (c.close - cand.entry) / avg
            rng = c.high - c.low
            rej = (c.high - max(c.open, c.close)) / rng if rng else 0.0
        else:
            prior = (cand.hi - min(x.low for x in before)) / avg if before else 0.0
            dist = (cand.entry - c.close) / avg
            rng = c.high - c.low
            rej = (min(c.open, c.close) - c.low) / rng if rng else 0.0
        room = obstacle_room(self.candles, cand.direction, k, c.close, avg, self.p.ztd_lookback,
                             self.p.max_width) if self.p.measure_context else None
        mid = (cand.hi + cand.lo) / 2
        sides = [x.close > mid for x in zone]
        crossings = sum(a != b for a, b in zip(sides, sides[1:]))
        return {"F1_prior_move": prior, "F2_vela0_size": (c.high - c.low) / avg, "F3_close_dist": dist,
                "F4_rejection": rej, "F5_room": room, "F6_crossings": crossings,
                "F7_broken_zone": None}  # F-7: método de la zona rota por definir en T15


def detect(candles, params: Params):
    """Recorre la serie vela a vela. Devuelve (señales, descartes)."""
    d = Detector(params)
    for c in candles:
        d.update(c)
    return d.signals, d.discards

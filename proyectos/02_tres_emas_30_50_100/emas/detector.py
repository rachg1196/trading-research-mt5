"""Detector del patrón de 3 EMAs (docs/STRATEGY_RULES.md, Rev. 5).

Causal: en la vela i solo se usan las velas 0..i, todas cerradas.
Se programa la COMPRA. La VENTA es el espejo exacto: se ejecuta la misma lógica
sobre las velas reflejadas (precio -> K - precio), así ambas son idénticas por
construcción. Las EMAs y la vela media se reflejan igual (son lineales).

Estados (compra):
  ESPERA_CRUCE  tras un patrón (señal o anulado) no se busca otro hasta un
                nuevo cruce de EMAs (consecuencia de P-06).
  BUSCA_TOQUE   desde el último cruce se espera el primer toque a la EMA 30
                (U-3b) en una vela con las EMAs ordenadas y separadas (D-022).
                El máximo es la vela más alta desde el cruce hasta la vela
                anterior al toque (P-07, D-021).
  RETROCESO     tocó la EMA 30; se espera la ruptura de la zona (U-3d).
  ROTO          rompió la zona; se espera la vela de confirmación (U-3e).

Orden + separación (P-01, P-11) se exigen desde la vela del máximo hasta la de
confirmación; P-02 se comprueba en la vela de confirmación (D-021).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .indicators import ema, vela_media

ESPERA_CRUCE, BUSCA_TOQUE, RETROCESO, ROTO = range(4)


@dataclass(frozen=True)
class Params:
    """Parámetros P-01..P-13 (valores por defecto de STRATEGY_RULES Rev. 5).

    P-14 (operaciones simultáneas) y P-15 (retraso simulado) son del backtest,
    no del detector; el retraso se calcula con entrada_tardia().
    """
    separacion: float = 0.25          # P-01, en velas medias
    velas_desde_cruce: int = 10       # P-02, comprobado en la vela de confirmación
    tolerancia_toque: float = 0.0     # P-03 (y P-12), en velas medias
    ema_vela_anterior: bool = False   # P-04: False = EMA de la misma vela
    ruptura: str = "cierre"           # P-05: "cierre" o "mecha"
    solo_primer_retroceso: bool = True  # P-06
    max_velas_maximo_toque: int | None = 20     # P-08 (None = sin límite)
    max_velas_toque_ruptura: int | None = 20    # P-09
    max_velas_ruptura_confirmacion: int | None = 10  # P-10
    alineadas_todo_el_patron: bool = True  # P-11
    altura_minima_zona: float = 0.0   # P-13, en velas medias (la zona debe ser > este valor)
    calentamiento: int = 500          # D-013: primeras velas sin buscar patrones


@dataclass(frozen=True)
class Signal:
    direccion: str      # "compra" o "venta"
    vela_maximo: int    # vela del máximo (mínimo en venta)
    vela_toque: int     # primer toque a la EMA 30
    vela_ruptura: int
    vela_confirmacion: int
    vela_entrada: int   # apertura de esta vela (confirmación + 1)
    vela_salida: int    # cierre de esta vela (confirmación + 4)
    zona_baja: float    # límites de la zona en precios reales
    zona_alta: float


def entrada_tardia(vela_confirmacion, velas_pasadas):
    """U-5: señal detectada tarde, sin reiniciar el conteo.

    velas_pasadas = velas ya cerradas después de la de confirmación cuando se
    detecta la señal. Devuelve (vela de entrada, vela de salida) o None si ya
    pasaron 4 o más.
    """
    if velas_pasadas < 0:
        raise ValueError("velas_pasadas no puede ser negativo")
    if velas_pasadas >= 4:
        return None
    return vela_confirmacion + 1 + velas_pasadas, vela_confirmacion + 4


def _a_arrays(velas):
    df = pd.DataFrame(velas)
    return tuple(df[c].to_numpy(dtype=float) for c in ("open", "high", "low", "close"))


def _detectar_compras(o, h, l, c, p):
    """Lógica de compra. Devuelve (señales, eventos)."""
    n = len(c)
    e30, e50, e100 = ema(c, 30), ema(c, 50), ema(c, 100)
    vm = vela_media(h, l)

    orden = (e100 < e50) & (e50 < e30)
    separadas = ((e30 - e50) >= p.separacion * vm) & ((e50 - e100) >= p.separacion * vm)
    alineada = orden & separadas

    # Cruce = cambia el orden relativo de algún par de EMAs respecto a la vela anterior.
    codigo = np.stack([np.sign(e30 - e50), np.sign(e50 - e100), np.sign(e30 - e100)], axis=1)
    cruce = np.zeros(n, dtype=bool)
    cruce[1:] = np.any(codigo[1:] != codigo[:-1], axis=1)
    ultimo_cruce = np.zeros(n, dtype=int)
    for i in range(1, n):
        ultimo_cruce[i] = i if cruce[i] else ultimo_cruce[i - 1]

    def ema_ref(arr, i):
        # P-04: EMA de la misma vela o de la anterior.
        return arr[i - 1] if p.ema_vela_anterior else arr[i]

    def toca(i, arr):
        # Tocar = la mecha (mínimo) llega a la EMA, con tolerancia P-03 / P-12.
        return l[i] <= ema_ref(arr, i) + p.tolerancia_toque * vm[i]

    def pasado(limite, desde, i):
        return limite is not None and i - desde > limite

    senales, eventos = [], []
    # Siempre se empieza esperando un cruce: el máximo se mide desde él (D-014 n.º 1).
    estado = ESPERA_CRUCE
    origen = m = t = b = -1
    techo = suelo = np.nan

    def terminar(i, motivo):
        nonlocal estado, origen
        eventos.append((i, "anulado", motivo))
        if p.solo_primer_retroceso:
            estado = ESPERA_CRUCE
        else:
            # P-06 = cualquiera: el siguiente máximo se busca desde donde acabó este patrón.
            estado, origen = BUSCA_TOQUE, i

    for i in range(max(p.calentamiento, 1), n):
        if cruce[i]:
            if estado in (ESPERA_CRUCE, BUSCA_TOQUE):
                estado, origen = BUSCA_TOQUE, i
                continue  # la vela del cruce no cuenta como toque

        if estado == ESPERA_CRUCE:
            continue

        if estado == BUSCA_TOQUE:
            # Solo cuenta un toque con las EMAs ordenadas Y separadas (D-022); un toque con
            # las EMAs pegadas no es un retroceso de tendencia y no gasta el patrón.
            if not alineada[i] or not toca(i, e30):
                continue
            # Primer retroceso. El máximo es la vela más alta entre el cruce y la vela
            # anterior al toque (P-07; en empate, la última). No se busca otro.
            tramo = h[origen:i]
            m = origen + len(tramo) - 1 - int(np.argmax(tramo[::-1]))
            t = i
            techo, suelo = h[m], max(o[m], c[m])
            eventos.append((i, "toque_ema30", f"maximo={m}"))
            if pasado(p.max_velas_maximo_toque, m, t):
                terminar(i, "P-08 maximo demasiado lejos del toque")
            elif not techo - suelo > p.altura_minima_zona * vm[m]:
                terminar(i, "P-13 zona sin altura")
            elif p.alineadas_todo_el_patron and not alineada[m:t + 1].all():
                terminar(i, "P-11 EMAs sin orden o sin separacion")
            elif toca(i, e100):
                terminar(i, "toco la EMA 100")
            else:
                estado = RETROCESO
            continue

        # RETROCESO o ROTO: la alineación debe mantenerse (P-11).
        if p.alineadas_todo_el_patron and not alineada[i]:
            terminar(i, "P-11 EMAs sin orden o sin separacion")
            continue

        if estado == RETROCESO:
            if toca(i, e100):
                terminar(i, "toco la EMA 100")
                continue
            rompe = c[i] > techo if p.ruptura == "cierre" else h[i] > techo
            if rompe:
                if pasado(p.max_velas_toque_ruptura, t, i):
                    terminar(i, "P-09 ruptura demasiado tarde")
                    continue
                estado, b = ROTO, i
                eventos.append((i, "ruptura", ""))
            elif pasado(p.max_velas_toque_ruptura, t, i):
                terminar(i, "P-09 sin ruptura a tiempo")
            continue

        if estado == ROTO:
            # Segundo retroceso (velas posteriores a la ruptura): llegar a la EMA 30 anula
            # (A-4); la vela de confirmación tampoco puede tocarla (A-1).
            if toca(i, e30):
                terminar(i, "segundo retroceso toco la EMA 30")
                continue
            if l[i] <= techo:  # toca la zona (U-3e)
                if c[i] < suelo:
                    terminar(i, "cierre por debajo de la zona")
                    continue
                if not p.alineadas_todo_el_patron and not alineada[i]:
                    terminar(i, "P-11 EMAs sin orden o sin separacion")
                    continue
                if i - ultimo_cruce[i] < p.velas_desde_cruce:
                    terminar(i, "P-02 cruce demasiado reciente")
                    continue
                senales.append((m, t, b, i, suelo, techo))
                eventos.append((i, "senal", ""))
                if p.solo_primer_retroceso:
                    estado = ESPERA_CRUCE
                else:
                    estado, origen = BUSCA_TOQUE, i
                continue
            if pasado(p.max_velas_ruptura_confirmacion, b, i):
                terminar(i, "P-10 sin confirmacion a tiempo")
            continue

    return senales, eventos


def detectar(velas, params=Params(), direccion="ambas", con_eventos=False):
    """Busca patrones en velas cerradas (DataFrame o dict con open, high, low, close).

    Devuelve la lista de Signal ordenada por vela de confirmación; con
    con_eventos=True devuelve además {direccion: eventos} para depurar.
    """
    o, h, l, c = _a_arrays(velas)
    resultado, todos_eventos = [], {}
    if direccion in ("ambas", "compra"):
        senales, ev = _detectar_compras(o, h, l, c, params)
        todos_eventos["compra"] = ev
        resultado += [Signal("compra", m, t, b, k, k + 1, k + 4, s, tc)
                      for m, t, b, k, s, tc in senales]
    if direccion in ("ambas", "venta"):
        # Espejo: precio -> K - precio; el máximo y el mínimo se intercambian.
        K = float(np.nanmax(h) + np.nanmin(l))
        senales, ev = _detectar_compras(K - o, K - l, K - h, K - c, params)
        todos_eventos["venta"] = ev
        resultado += [Signal("venta", m, t, b, k, k + 1, k + 4, K - tc, K - s)
                      for m, t, b, k, s, tc in senales]
    resultado.sort(key=lambda s: (s.vela_confirmacion, s.direccion))
    return (resultado, todos_eventos) if con_eventos else resultado

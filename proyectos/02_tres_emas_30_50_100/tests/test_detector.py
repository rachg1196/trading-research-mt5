"""Pruebas del detector con velas inventadas (sin MT5)."""
import math

import numpy as np
import pytest

from candles import Velas, espejo, patron_compra, preambulo
from emas.detector import Params, detectar, entrada_tardia
from emas.indicators import ema, vela_media


def escenario(**variante):
    v = Velas()
    preambulo(v)
    info = patron_compra(v, **variante)
    return v, info


def motivos(eventos):
    return [m for _, tipo, m in eventos if tipo == "anulado"]


# --- Indicadores calculados a mano ---------------------------------------

def test_ema_a_mano():
    # alfa = 2/(3+1) = 0,5: 1 -> 1,5 -> 2,25 -> 3,125
    assert ema([1, 2, 3, 4], 3) == pytest.approx([1, 1.5, 2.25, 3.125])
    # n = 30: alfa = 2/31; segundo valor = 10 + (2/31)*(20-10)
    assert ema([10, 20], 30)[1] == pytest.approx(10 + 20 / 31)


def test_vela_media_a_mano():
    rangos = np.arange(1, 26, dtype=float)  # rangos 1, 2, ..., 25
    vm = vela_media(rangos, np.zeros(25))
    assert math.isnan(vm[18])               # aún no hay 20 velas
    assert vm[19] == pytest.approx(10.5)    # media de 1..20
    assert vm[24] == pytest.approx(15.5)    # media de 6..25


# --- Patrón válido --------------------------------------------------------

def test_patron_valido_como_la_imagen():
    v, info = escenario()
    senales = detectar(v.df())
    assert len(senales) == 1
    s = senales[0]
    assert s.direccion == "compra"
    assert (s.vela_maximo, s.vela_toque, s.vela_ruptura, s.vela_confirmacion) == (
        info["maximo"], info["toque"], info["ruptura"], info["confirmacion"])
    assert s.vela_entrada == info["confirmacion"] + 1   # U-3g
    assert s.vela_salida == info["confirmacion"] + 4    # U-4
    assert (s.zona_baja, s.zona_alta) == (info["suelo"], info["techo"])


def test_confirmacion_que_cierra_dentro_de_la_zona_vale():
    v, info = escenario(confirmacion="dentro")
    assert [s.vela_confirmacion for s in detectar(v.df())] == [info["confirmacion"]]


def test_retroceso_hasta_la_ema_50_vale():
    v, info = escenario(toque="e50")
    assert [s.vela_confirmacion for s in detectar(v.df())] == [info["confirmacion"]]


def test_vela_del_maximo_roja():
    v, info = escenario(maximo_rojo=True)
    s, = detectar(v.df())
    assert s.zona_baja == v.o[info["maximo"]]  # A-5: desde max(apertura, cierre)
    assert s.zona_alta == v.h[info["maximo"]]


# --- Cancelaciones --------------------------------------------------------

def test_cierre_bajo_la_zona_cancela():
    v, _ = escenario(confirmacion="debajo")
    senales, ev = detectar(v.df(), con_eventos=True)
    assert senales == []
    assert "cierre por debajo de la zona" in motivos(ev["compra"])


def test_tocar_la_ema_100_cancela():
    v, _ = escenario(toque="e100")
    senales, ev = detectar(v.df(), con_eventos=True)
    assert senales == []
    assert "toco la EMA 100" in motivos(ev["compra"])


def test_confirmacion_que_toca_la_ema_30_no_vale():
    v, _ = escenario(confirmacion="toca_e30")
    senales, ev = detectar(v.df(), con_eventos=True)
    assert senales == []
    assert "segundo retroceso toco la EMA 30" in motivos(ev["compra"])


def test_vela_de_ruptura_no_es_confirmacion():
    v, _ = escenario(ruptura_en_zona=True, sin_retesteo=True)
    senales, ev = detectar(v.df(), con_eventos=True)
    assert senales == []
    assert "P-10 sin confirmacion a tiempo" in motivos(ev["compra"])


def test_confirmacion_demasiado_tarde_cancela():
    v, _ = escenario(velas_entre_ruptura_y_retesteo=12)
    senales, ev = detectar(v.df(), con_eventos=True)
    assert senales == []
    assert "P-10 sin confirmacion a tiempo" in motivos(ev["compra"])


# --- EMAs pegadas o cruzadas ---------------------------------------------

def test_emas_pegadas_no_vale():
    # Separación EMA30-EMA50 ~5 precios; con P-01 = 5 velas medias (~5,5) quedan "pegadas".
    v, _ = escenario()
    senales, ev = detectar(v.df(), Params(separacion=5.0), con_eventos=True)
    assert senales == []
    # Con las EMAs pegadas el toque no es un retroceso: no se abre ningún patrón (D-022).
    assert not any(tipo == "toque_ema30" for _, tipo, _ in ev["compra"])


def test_emas_que_se_juntan_durante_el_patron_cancelan():
    # Tras el toque, el precio se queda bajo la EMA 50 (sin llegar a la 100): la EMA 30
    # se pega a la 50. Sin límite P-09, para que la única causa posible sea P-11.
    v = Velas()
    preambulo(v)
    v.tendencia(5, +1.0)
    v.vela(v.ultimo + 1.0, high=v.ultimo + 2.0)
    for _ in range(60):
        v.vela(ema(v.c, 50)[-1] - 1.0)
    senales, ev = detectar(v.df(), Params(max_velas_toque_ruptura=None), con_eventos=True)
    assert senales == []
    assert "P-11 EMAs sin orden o sin separacion" in motivos(ev["compra"])


def test_emas_recien_cruzadas_no_vale():
    # El último cruce está a ~100 velas del patrón; si se exigen 1000 velas sin cruce, no vale.
    v, _ = escenario()
    senales, ev = detectar(v.df(), Params(velas_desde_cruce=1000), con_eventos=True)
    assert senales == []
    assert "P-02 cruce demasiado reciente" in motivos(ev["compra"])  # se mira en la confirmación


# --- Caso A5: el máximo es el más alto desde el cruce (D-021) -------------

def escenario_a5():
    """Como la A5 (FlipX 2 H3, 2024-06-21): justo tras el cruce hay una vela muy alta,
    cuando las EMAs aún no están separadas; luego se separan y llega un retroceso desde
    un máximo menor. Devuelve las velas, la vela alta y el patrón del máximo menor."""
    v = Velas()
    v.tendencia(520, -0.5)
    while not v.ema_actual(100) < v.ema_actual(50) < v.ema_actual(30):
        v.tendencia(1, +0.5)                     # sube hasta el último cruce
    alta = v.vela(v.ultimo + 0.5, high=v.ultimo + 20.0)
    v.tendencia(8, +0.5)
    return v, alta, patron_compra(v)


def test_caso_a5_maximo_mas_alto_desde_el_cruce_sin_separacion_no_vale():
    v, alta, info = escenario_a5()
    df = v.df()
    # Con la regla anterior el máximo era el menor y había señal; con la corregida
    # el máximo es la vela alta y, como ahí las EMAs no están separadas, no vale.
    assert max(v.h[alta + 1: info["toque"]]) < v.h[alta]
    senales, ev = detectar(df, direccion="compra", con_eventos=True)
    assert senales == []
    toques = [inf for _, tipo, inf in ev["compra"] if tipo == "toque_ema30"]
    assert toques[0] == f"maximo={alta}"
    assert motivos(ev["compra"])[0] == "P-11 EMAs sin orden o sin separacion"
    # Sin exigir separación (P-01 = 0) el mismo máximo alto sí se acepta como máximo:
    # el precio no supera su mecha, así que tampoco hay señal (como dijo el usuario).
    _, ev0 = detectar(df, Params(separacion=0.0), direccion="compra", con_eventos=True)
    assert [inf for _, tipo, inf in ev0["compra"] if tipo == "toque_ema30"][0] == f"maximo={alta}"


def test_toque_con_emas_pegadas_no_gasta_el_patron():
    # Justo tras el cruce (EMA 50 y 100 aún pegadas) una vela toca la EMA 30: no cuenta.
    # El siguiente toque, ya con separación, sí es el primer retroceso (D-022).
    v = Velas()
    v.tendencia(520, -0.5)
    while not v.ema_actual(100) < v.ema_actual(50) < v.ema_actual(30):
        v.tendencia(1, +0.5)
    pegado = v.vela(v.ultimo + 0.5)
    v.poner_minimo(pegado, v.ema_actual(30) - 0.1)
    e30, e50, e100 = (ema(v.c, n)[pegado] for n in (30, 50, 100))
    vm = vela_media(v.h, v.l)[pegado]
    assert e100 < e50 < e30 and (e50 - e100) < 0.25 * vm   # ordenadas pero pegadas
    v.tendencia(15, +0.5)
    info = patron_compra(v)
    senales, ev = detectar(v.df(), direccion="compra", con_eventos=True)
    assert [(s.vela_maximo, s.vela_toque, s.vela_confirmacion) for s in senales] == [
        (info["maximo"], info["toque"], info["confirmacion"])]
    assert [i for i, tipo, _ in ev["compra"] if tipo == "toque_ema30"] == [info["toque"]]
    ventas = detectar(espejo(v.df()), direccion="venta")
    assert [s.vela_confirmacion for s in ventas] == [info["confirmacion"]]


def test_caso_a5_espejo_en_venta():
    v, alta, _ = escenario_a5()
    _, ev_c = detectar(v.df(), direccion="compra", con_eventos=True)
    senales, ev_v = detectar(espejo(v.df()), direccion="venta", con_eventos=True)
    assert senales == []
    assert ev_v["venta"] == ev_c["compra"]
    assert [inf for _, tipo, inf in ev_v["venta"] if tipo == "toque_ema30"][0] == f"maximo={alta}"


# --- Solo el primer retroceso (consecuencia de P-06) ----------------------

def test_tras_un_patron_no_hay_otro_hasta_nuevo_cruce_y_realineacion():
    v = Velas()
    preambulo(v)
    primero = patron_compra(v)
    v.tendencia(40, +0.5)
    patron_compra(v)                       # misma tendencia, sin cruce: no cuenta
    v.tendencia(200, -0.5)                 # las EMAs se cruzan...
    v.tendencia(160, +0.5)                 # ...y se vuelven a alinear
    tercero = patron_compra(v)
    compras = [s.vela_confirmacion for s in detectar(v.df()) if s.direccion == "compra"]
    assert compras == [primero["confirmacion"], tercero["confirmacion"]]
    # Con P-06 = "cualquiera", el segundo patrón sí cuenta (lo bloquea P-06, no otra cosa).
    todos = detectar(v.df(), Params(solo_primer_retroceso=False), direccion="compra")
    assert len(todos) == 3


# --- Señales tardías (U-5) -----------------------------------------------

@pytest.mark.parametrize("pasadas, esperado", [
    (0, (101, 104)),   # a tiempo: 4 velas
    (1, (102, 104)),   # pasó 1: quedan 3
    (3, (104, 104)),   # pasaron 3: queda 1
    (4, None),         # 4 o más: no se entra
    (7, None),
])
def test_senal_tardia(pasadas, esperado):
    assert entrada_tardia(100, pasadas) == esperado


# --- Venta: espejo exacto -------------------------------------------------

VARIANTES = [
    {}, {"confirmacion": "dentro"}, {"toque": "e50"}, {"maximo_rojo": True},
    {"confirmacion": "debajo"}, {"toque": "e100"}, {"confirmacion": "toca_e30"},
    {"ruptura_en_zona": True, "sin_retesteo": True}, {"velas_entre_ruptura_y_retesteo": 12},
]


@pytest.mark.parametrize("variante", VARIANTES)
def test_venta_es_el_espejo_de_la_compra(variante):
    v, _ = escenario(**variante)
    compras = detectar(v.df(), direccion="compra")
    ventas = detectar(espejo(v.df()), direccion="venta")
    clave = lambda s: (s.vela_maximo, s.vela_toque, s.vela_ruptura,
                       s.vela_confirmacion, s.vela_entrada, s.vela_salida)
    assert [clave(s) for s in ventas] == [clave(s) for s in compras]
    assert all(s.direccion == "venta" for s in ventas)


def test_venta_valida_y_zona_en_la_mecha_inferior():
    v, info = escenario()
    df = espejo(v.df())
    s, = detectar(df)                       # solo la venta, ninguna compra
    assert s.direccion == "venta"
    k = info["maximo"]
    assert s.zona_baja == pytest.approx(df["low"][k])
    assert s.zona_alta == pytest.approx(min(df["open"][k], df["close"][k]))


# --- Causalidad y calentamiento ------------------------------------------

def test_es_causal_las_velas_futuras_no_cambian_el_pasado():
    v, info = escenario()
    df = v.df()
    k = info["confirmacion"]
    for corte in range(k - 3, len(df)):
        senales = detectar(df.iloc[: corte + 1])
        assert [s.vela_confirmacion for s in senales] == ([k] if corte >= k else [])
    # Añadir velas locas al final tampoco cambia la señal pasada.
    v.tendencia(50, -5.0)
    assert detectar(v.df())[0].vela_confirmacion == k


def test_no_se_buscan_patrones_en_el_calentamiento():
    v = Velas()
    preambulo(v, bajada=200, subida=160)   # el patrón queda antes de la vela 500
    info = patron_compra(v)
    v.tendencia(200, +0.5)
    assert info["confirmacion"] < 500
    assert detectar(v.df(), direccion="compra") == []
    assert len(detectar(v.df(), Params(calentamiento=100), direccion="compra")) == 1

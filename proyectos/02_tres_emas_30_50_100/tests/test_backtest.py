"""Pruebas de los cálculos del backtest (BACKTEST_PLAN §11): precio, coste, salida, control y Holm."""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from backtest import control, drawdown, holm, noches, resultado, spread_efectivo, una_a_la_vez  # noqa: E402


def test_spread_cero_usa_el_de_la_especificacion():
    sp, prudente = spread_efectivo([0, 120, 90], espec=100, mediana=100)
    assert not prudente
    assert list(sp) == [100, 120, 90]


def test_spread_prudente_si_la_mediana_es_baja():
    sp, prudente = spread_efectivo([50, 120, 0], espec=100, mediana=70)   # 70 < 80 % de 100
    assert prudente
    assert list(sp) == [100, 120, 100]


def test_compra_y_venta_con_costes():
    o = np.array([10.0, 10.0, 10.0, 10.0])
    c = np.array([10.0, 10.0, 10.0, 12.0])
    sp = np.array([100.0, 100.0, 100.0, 200.0])   # puntos; punto = 0,01 -> 1,0 y 2,0 de precio
    e, x = np.array([0, 0]), np.array([3, 3])
    compra = np.array([True, False])
    neto, c_sp, c_de, c_sw = resultado(o, c, sp, 0.01, e, x, compra, 0.5, np.array([0.0, 0.0]), np.array([0, 0]))
    # Compra: entra a 10 + 1 + 0,5, sale a 12 − 1 -> 11 − 11,5 = −0,5
    assert neto[0] == pytest.approx(-0.5)
    # Venta: entra a 10 − 0,5, sale a 12 + 2 + 1 -> 9,5 − 15 = −5,5
    assert neto[1] == pytest.approx(-5.5)
    assert list(c_sp) == pytest.approx([1.0, 2.0])
    assert list(c_de) == pytest.approx([1.5, 1.5])


def test_swap_por_noche_y_triple_en_viernes():
    jueves, viernes = date(2026, 10, 15).toordinal(), date(2026, 10, 16).toordinal()
    dia = np.array([jueves, jueves, viernes, viernes + 1, viernes + 2])
    assert noches(dia, np.array([0]), np.array([1]), 5)[0] == 0   # mismo día
    assert noches(dia, np.array([0]), np.array([2]), 5)[0] == 1   # jueves -> viernes
    assert noches(dia, np.array([2]), np.array([3]), 5)[0] == 3   # viernes -> sábado: triple
    assert noches(dia, np.array([0]), np.array([4]), 5)[0] == 5   # 1 + 3 + 1
    neto, _, _, c_sw = resultado(np.ones(5), np.ones(5), np.zeros(5), 0.01, np.array([2]), np.array([3]),
                                 np.array([True]), 0.0, np.array([-1.5]), np.array([3]))
    assert c_sw[0] == pytest.approx(4.5) and neto[0] == pytest.approx(-4.5)


def test_una_operacion_a_la_vez():
    # Salida = entrada + 3. La de la vela 3 entra cuando la primera aún está abierta (sale en la 3).
    e = np.array([0, 3, 4, 9])
    assert list(una_a_la_vez(e, e + 3)) == [0, 2, 3]


def test_control_misma_n_y_resultados_conocidos():
    rng = np.random.default_rng(1)
    vm_c, vm_v = np.full(100, 2.0), np.full(100, -1.0)
    pool = np.arange(10, 90)
    suma, cuenta = control(rng, 4, 3, vm_c, vm_v, pool, pool, reps=200)
    media = suma / cuenta
    assert np.all(cuenta <= 4) and np.mean(cuenta == 4) > 0.5
    assert np.all((media >= -1.0) & (media <= 2.0))
    # Sin solapes (vela única por dirección muy separada), la media es exacta: (3×2 − 1) / 4.
    suma, cuenta = control(rng, 2, 1, vm_c, vm_v, np.array([10]), np.array([50]), reps=5)
    assert list(cuenta) == [2] * 5 and list(suma) == pytest.approx([1.0] * 5)


def test_holm():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5, 0.001]) == pytest.approx([0.5, 0.002])


def test_drawdown():
    assert drawdown(np.array([1.0, -2.0, -1.0, 3.0])) == pytest.approx(3.0)
    assert drawdown(np.array([])) == 0.0

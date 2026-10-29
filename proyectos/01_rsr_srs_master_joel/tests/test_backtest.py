"""Pruebas de los cálculos del backtest (BACKTEST_PLAN §3, §5 y §8): precios, costes, solapamiento y Holm."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import backtest as bt  # noqa: E402


class Costs(unittest.TestCase):
    o = np.array([100.0, 101.0, 102.0, 103.0])
    c = np.array([100.5, 101.5, 102.5, 104.0])
    sp = np.array([100.0, 100.0, 100.0, 200.0])   # puntos (0,01): 1,00 y 2,00 de precio

    def test_compra_paga_spread_al_entrar_y_deslizamiento(self):
        # entra a 101 + 1 (spread) + 0,5 (deslizamiento) = 102,5; sale a 104 − 1 (0,5 × 2,00) = 103 → +0,5
        self.assertAlmostEqual(bt.trade_pnl(self.o, self.c, self.sp, 1, 3, True, 0.5), 0.5)

    def test_venta_paga_spread_al_salir(self):
        # entra a 101 − 0,5 = 100,5; sale a 104 + 2 + 1 = 107 → −6,5
        self.assertAlmostEqual(bt.trade_pnl(self.o, self.c, self.sp, 1, 3, False, 0.5), -6.5)

    def test_sin_deslizamiento(self):
        self.assertAlmostEqual(bt.trade_pnl(self.o, self.c, self.sp, 1, 3, True, 0.0), 2.0)

    def test_spread_prudente(self):
        s, prudent = bt.spreads("BreakX600", np.array([0.0, 65.0, 130.0, 65.0]))
        self.assertTrue(prudent)
        self.assertEqual(s.tolist(), [130.0, 130.0, 130.0, 130.0])
        s, prudent = bt.spreads("FXVol20", np.array([374.0, 380.0]))
        self.assertFalse(prudent)
        self.assertEqual(s.tolist(), [374.0, 380.0])

    def test_swap(self):
        self.assertEqual(bt.nights_between("2025-01-02 23:55", "2025-01-03 00:10"), 1)
        self.assertEqual(bt.nights_between("2025-01-02 10:00", "2025-01-02 11:00"), 0)
        self.assertAlmostEqual(bt.swap_cost("FlipX1", True, 80000, 1), -1.0)
        self.assertAlmostEqual(bt.swap_cost("FXVol20", False, 100000, 1), -2.0 / 100 * 100000 / 360)


class Rules(unittest.TestCase):
    def test_una_operacion_abierta(self):
        entries = np.array([10, 11, 14, 15, 20])
        taken = bt.account(entries, entries + 3)
        self.assertEqual(entries[taken].tolist(), [10, 14, 20])   # 11 (abierta hasta 13) y 15 (hasta 17) se ignoran

    def test_holm(self):
        self.assertEqual(bt.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

    def test_drawdown(self):
        self.assertAlmostEqual(bt.drawdown(np.array([1.0, -3.0, 1.0, -1.0, 5.0])), 3.0)


if __name__ == "__main__":
    unittest.main()

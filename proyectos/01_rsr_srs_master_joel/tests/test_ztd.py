"""Pruebas de la ZTD horizontal y del F-5 redefinido (D-019). Series sintéticas; los valores no son reglas."""
import unittest
from dataclasses import replace

from rsr_srs import BUY, Candle, Params, detect
from rsr_srs.ztd import horizontal_ztd, htf_index

from tests.test_detector import FLAT, DROP, Z1, Z2, FAKE, INSIDE, BREAK, Z0, at_zone, mirror

P = Params(max_width=2.0, max_total=12, avg_n=20, wick="b")
HIST = [(100, 105, 95, 100)] * 20
RISE = (100, 112, 99, 110)
PRIOR = [(110, 120, 108, 118), (118, 121, 112, 114)]   # zona previa: alto 121, bajo 108
HOLD = (114, 119, 110, 112)                           # la frena: no cierra por encima de 121
BRK = (112, 130, 111, 128)                            # la rompe hacia arriba (cierra en 128)
RETEST = [(128, 135, 126, 133), (133, 136, 124, 126), (126, 130, 122, 128), (128, 131, 123, 125)]
PAT = [(125, 126, 119, 123), (123, 130, 122, 129), (129, 140, 128, 138)]   # engaño, dentro, vela 0


def build(rows):
    return [Candle(i, *r) for i, r in enumerate(rows)]


class HorizontalZTD(unittest.TestCase):
    def signal(self, rows, params=P):
        sig, _ = detect(build(rows), params)
        return [s for s in sig if s.direction == BUY and s.vela0_index == len(rows) - 1]

    def test_rota_y_retesteada_desde_arriba(self):
        """Compra: zona que frenó por arriba, rota hacia arriba y retesteada; el patrón se forma en el retesteo."""
        s = self.signal(HIST + [RISE] + PRIOR + [HOLD, BRK] + RETEST + PAT)
        self.assertEqual(len(s), 1)
        z = s[0].context["ztd_detail"]
        self.assertTrue(s[0].context["ztd_horizontal"])
        self.assertEqual((z["high"], z["low"], z["primer_toque"]), (121, 108, True))
        self.assertLess(z["end"], s[0].zone_start)          # distinta de la zona del patrón (D-019, ajuste 1)

    def test_sin_ruptura_no_hay_ztd(self):
        rows = HIST + [RISE] + PRIOR + [HOLD, (112, 120.5, 111, 120)] + RETEST + PAT
        s = self.signal(rows)
        self.assertEqual(len(s), 1)
        self.assertFalse(s[0].context["ztd_horizontal"])

    def test_distancia_maxima(self):
        rows = HIST + [RISE] + PRIOR + [HOLD, BRK] + RETEST + PAT
        self.assertTrue(self.signal(rows)[0].context["ztd_horizontal"])
        self.assertFalse(self.signal(rows, replace(P, ztd_dist=0.05))[0].context["ztd_horizontal"])

    def test_volvio_a_cerrar_por_debajo(self):
        """Si tras la ruptura una vela cierra por debajo del nivel bajo de la zona previa, ya no cuenta como rota."""
        ok = HIST + [RISE] + PRIOR + [HOLD, BRK] + RETEST
        bad = HIST + [RISE] + PRIOR + [HOLD, BRK, (128, 129, 100, 105), (105, 128, 104, 127)] + RETEST
        args = lambda rows: (build(rows), BUY, len(rows) - 4, 122, 136, 10.0, 100, 1.0, 0.5, 2.0)
        self.assertEqual(horizontal_ztd(*args(ok))["high"], 121)
        z = horizontal_ztd(*args(bad))
        self.assertTrue(z is None or z["high"] != 121)

    def test_filtro_opcional(self):
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, BREAK]      # sin ZTD
        self.assertEqual(len(at_zone(detect(build(rows), P)[0], Z0)), 1)
        self.assertEqual(at_zone(detect(build(rows), replace(P, require_ztd=True))[0], Z0), [])

    def test_venta_espejo(self):
        rows = mirror(HIST + [RISE] + PRIOR + [HOLD, BRK] + RETEST + PAT, axis=300)
        sig, _ = detect(build(rows), P)
        s = [x for x in sig if x.direction == "RSR" and x.vela0_index == len(rows) - 1]
        self.assertTrue(s and s[0].context["ztd_horizontal"])


class ObstacleF5(unittest.TestCase):
    def test_zona_intacta_por_delante(self):
        """F-5: la zona plana de 195-205 frenó el precio y sigue intacta por encima de la vela 0."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, BREAK]
        s = at_zone(detect(build(rows), P)[0], Z0)[0]
        self.assertAlmostEqual(s.measures["F5_room"], (195 - BREAK[3]) / s.avg_candle)

    def test_sin_obstaculo(self):
        s = [x for x in detect(build(HIST + [RISE] + PRIOR + [HOLD, BRK] + RETEST + PAT), P)[0]
             if x.direction == BUY][-1]
        self.assertIsNone(s.measures["F5_room"])


class HigherTF(unittest.TestCase):
    def test_htf_index_solo_velas_cerradas(self):
        h1 = [Candle(f"2025-06-14 0{h}:00", 1, 2, 0, 1) for h in range(5)]
        self.assertEqual(htf_index(h1, "2025-06-14 03:00", 60), 3)   # 00, 01 y 02 cerradas; 03 abierta
        self.assertEqual(htf_index(h1, "2025-06-14 03:05", 60), 3)


if __name__ == "__main__":
    unittest.main()

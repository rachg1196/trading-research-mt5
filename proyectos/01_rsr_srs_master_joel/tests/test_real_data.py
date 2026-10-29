"""Pruebas con el historial real descargado en solo lectura (D-014): FX Vol 20 M15/H4 y FlipX 4 M15 (ago-sep 2025).
Comprueban causalidad e invariantes; la comparación con E2-07 (24 ago, niveles ~97.100/97.350) es informativa.
No es un backtest (D-015): no se simulan entradas ni salidas.
"""
import csv
import unittest
from dataclasses import replace
from pathlib import Path

from rsr_srs import BUY, Candle, Params, detect

HIST = Path(__file__).resolve().parent.parent / "analysis" / "mt5" / "history"
P = Params(max_width=3.0, max_total=12, avg_n=20, wick="b", max_fake=4)
# Elegidos solo con las ventanas de E2 (D-017, analysis/cases/eval_results.json). No son valores recomendados.
CHOSEN = Params(max_width=2.0, max_fake=5, max_total=24, avg_n=50, zone_pick="all", single_candle="inside", wick="b")


def load(name):
    with (HIST / name).open(encoding="utf-8") as f:
        return [Candle(r["time"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
                for r in csv.DictReader(f)]


# Solo los datos de los casos; los archivos largos del backtest (desde 2024-06/2024-12) se excluyen por tiempo.
FILES = sorted(p.name for p in HIST.glob("*.csv") if "_2024-12-01T" not in p.name and "_2024-06-01T" not in p.name) \
    if HIST.exists() else []


@unittest.skipUnless(FILES, "sin historial descargado")
class RealData(unittest.TestCase):
    def test_causal_e_invariantes(self):
        for name in FILES:
            with self.subTest(name):
                candles = load(name)
                sig, _ = detect(candles, P)
                part, _ = detect(candles[:len(candles) // 2], P)
                cut = len(candles) // 2
                self.assertEqual([(s.zone_start, s.vela0_index) for s in part],
                                 [(s.zone_start, s.vela0_index) for s in sig if s.vela0_index < cut])
                keys = [(s.direction, s.zone_start, s.zone_end) for s in sig]
                self.assertEqual(len(keys), len(set(keys)))
                for s in sig:
                    buy = s.direction == BUY
                    self.assertTrue(s.vela0.close > s.entry_level if buy else s.vela0.close < s.entry_level)
                    self.assertGreater(s.vela0_index, s.zone_end)

    def test_tc04_operacion_real_datos_reales(self):
        """TC-04 con velas reales (Weltrade-Demo; las velas 04:05, 04:10 y 04:50 coinciden con la ventana de datos
        del video Weltrade-Real): compra con vela 0 a las 04:10 del 14-06-2025 (C1306-P02, R-47)."""
        name = "FlipX4_M5_2025-06-12T0000_2025-06-15T0000.csv"
        if name not in FILES:
            self.skipTest("sin datos")
        sig, _ = detect(load(name), Params(max_width=3.0, max_total=20, avg_n=20, wick="b", max_fake=2))
        self.assertTrue([s for s in sig if s.direction == BUY and s.vela0.time == "2025-06-14 04:10"])

    def _hit(self, name, direction, vela0, upper, lower, err, params):
        """(acierto por hora, acierto por hora y zona). Tolerancia propuesta en D-017: max(error de lectura,
        0,25 velas medias) alrededor de los rectángulos que él dibujó."""
        if name not in FILES:
            self.skipTest(f"sin datos {name}")
        sig, _ = detect(load(name), params)
        g = [s for s in sig if s.direction == direction and s.vela0.time == vela0]
        inside = lambda v, b, t: min(b) - t <= v <= max(b) + t
        zones = [z for s in g for z in s.zones]         # S-10: todas las zonas que respaldan la señal
        return bool(g), any(inside(z["high"], upper, max(err, 0.25 * z["avg_candle"]))
                            and inside(z["low"], lower, max(err, 0.25 * z["avg_candle"])) for z in zones)

    def test_casos_e2_con_parametros_elegidos(self):
        """D-017: parámetros elegidos SOLO con E2 (tools/evaluate_windows.py). Hora y zona de sus rectángulos
        (bandas de analysis/cases/windows.json)."""
        cases = [("FXVol20_M15_2025-08-20T0000_2025-09-10T0000.csv", BUY, "2025-08-26 21:15",
                  (99722, 99798), (99430, 99545), 11),                                     # T-08
                 ("FlipX4_M15_2025-08-14T0000_2025-08-21T0000.csv", BUY, "2025-08-18 08:30",
                  (88745, 88797), (88605, 88648), 9),                                      # T-12a
                 ("FXVol20_M15_2025-08-20T0000_2025-09-10T0000.csv", "RSR", "2025-09-04 14:30",
                  (103026, 103085), (102627, 102739), 6),                                  # T-13
                 ("FXVol20_M5_2025-08-28T0000_2025-09-06T0000.csv", BUY, "2025-09-01 10:05",
                  (101964, 102002), (101812, 101868), 3),                                  # T-14
                 ("FlipX4_M5_2025-08-28T0000_2025-09-06T0000.csv", BUY, "2025-09-03 03:00",
                  (88791, 88818), (88711, 88735), 3)]                                      # T-15
        for c in cases:
            with self.subTest(c[2]):
                self.assertEqual(self._hit(*c, CHOSEN), (True, True))
        # T-09: acierta la hora, no la zona (fallo conocido, docs/DETECTOR_VALIDATION.md)
        self.assertEqual(self._hit("FXVol20_M15_2025-08-20T0000_2025-09-10T0000.csv", BUY, "2025-08-24 07:00",
                                   (97243, 97289), (97063, 97124), 8, CHOSEN), (True, False))

    def test_operaciones_reales_de_las_clases(self):
        """T-18 (compra real 04:10) y T-23 (venta real 05:35), con los parámetros elegidos con E2."""
        self.assertEqual(self._hit("FlipX4_M5_2025-06-12T0000_2025-06-15T0000.csv", BUY, "2025-06-14 04:10",
                                   (78429.9, 78459.9), (78335.5, 78367.3), 3, CHOSEN), (True, True))
        self.assertTrue(self._hit("FlipX3_M5_2025-06-12T0000_2025-06-15T0000.csv", "RSR", "2025-06-14 05:35",
                                  (119062.9, 119077.2), (119018.7, 119039.0), 3, CHOSEN)[0])

    def test_tc10_con_velas_reales_t29(self):
        """TC-10 con las velas reales de C1306-P09 @ 00:00-00:21 (T-29, FlipX 5 M5, 10-06-2025): con la zona de
        sus 2 rectángulos de abajo el engaño tiene 4 velas (A1, CLASS_CROSSCHECK §8). La hora sola no basta:
        15:30 también sale con zonas formadas dentro del engaño."""
        args = ("FlipX5_M5_2025-06-09T0000_2025-06-11T0000.csv", BUY, "2025-06-10 15:30",
                (87865.5, 87895.1), (87763.1, 87788.9), 2)
        for n, expected in ((2, False), (3, False), (4, True), (5, True)):
            with self.subTest(max_fake=n):
                self.assertEqual(self._hit(*args, replace(CHOSEN, max_fake=n))[1], expected)

    def test_informativo_e2_07(self):
        """Lista las compras del 24-25 ago en FX Vol 20 M15 con zona en ~97.000-97.450 (E2-07 @ 01:21-01:29)."""
        name = "FXVol20_M15_2025-08-20T0000_2025-09-10T0000.csv"
        if name not in FILES:
            self.skipTest("sin datos")
        sig, _ = detect(load(name), P)
        near = [s for s in sig if s.direction == BUY and s.vela0.time[:10] in ("2025-08-24", "2025-08-25")
                and 96950 <= s.level_low <= 97450]
        print(f"\n[informativo] compras en zona ~97.000-97.450 el 24-25 ago (M15): {len(near)}")
        for s in near:
            print(f"  vela 0 {s.vela0.time}  zona {s.level_low:.2f}-{s.level_high:.2f}  "
                  f"engaño {s.fake_candles}  velas zona {s.zone_end - s.zone_start + 1}")


if __name__ == "__main__":
    unittest.main()

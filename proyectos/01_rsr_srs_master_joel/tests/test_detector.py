"""Pruebas del detector (DETECTOR_SPEC Rev. 1 §7). Casos sintéticos y dibujos reconstruidos a partir de las
descripciones vela a vela de docs/PATTERN_STRUCTURE.md (verificadas visualmente por A2/A6); no son datos reales.
Los valores de los parámetros son de prueba, no reglas de Master Joel.

Uso:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""
import random
import unittest
from dataclasses import replace

from rsr_srs import BUY, SELL, Candle, Detector, Params, detect

P = Params(max_width=2.0, max_total=10, avg_n=20, wick="b")
FLAT = [(200, 205, 195, 200)] * 20          # historial para la vela media; no crea candidatos
DROP = (200, 202, 108, 110)                 # caída previa (R-06); corta la ventana de la zona
Z1, Z2 = (110, 118, 104, 114), (114, 119, 105, 108)   # zona de 2 velas: alto 119, bajo 104
FAKE = (108, 110, 99, 106)                  # engaño: perfora 104 y vuelve
INSIDE = (106, 117, 105, 116)               # llega "hasta aquí" y cierra dentro (C1306-P03 @ 00:24)
BREAK = (116, 126, 115, 125)                # cierra por encima de 119: vela 0
Z0 = len(FLAT) + 1                          # índice de la primera vela de la zona


def build(rows, t0=0):
    return [Candle(t0 + i, *r) for i, r in enumerate(rows)]


def mirror(rows, axis=300):
    """Espejo vertical: un SRS se convierte en RSR."""
    return [(axis - o, axis - lo, axis - hi, axis - c) for o, hi, lo, c in rows]


def run(rows, params=P):
    return detect(build(rows), params)


def at_zone(events, start, direction=BUY):
    """Eventos de una zona que empieza en `start`. Con S-10 (D-018) una señal puede tener varias zonas."""
    starts = lambda e: [z["start"] for z in e.zones] if hasattr(e, "zones") else [e.zone_start]
    return [e for e in events if start in starts(e) and e.direction == direction]


class SignalCases(unittest.TestCase):
    def test_tc01_srs_dibujo_dos_velas(self):
        """TC-01 C1306-P03 @ 00:00-00:24: compra; vale con P-1 rango y exactamente 2."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, BREAK]
        for p in (P, replace(P, zone_candles="exact2")):
            sig, _ = run(rows, p)
            s = at_zone(sig, Z0)
            self.assertEqual(len(s), 1)
            self.assertEqual((s[0].vela0_index, s[0].zone_end - s[0].zone_start + 1), (len(rows) - 1, 2))
            self.assertEqual((s[0].level_high, s[0].level_low, s[0].levels), (119, 104, "mismas"))

    def test_tc02_rsr_dibujo(self):
        """TC-02/TC-03 C0907-P03 @ 00:45-01:01, RSR-01 @ 00:33-01:05: venta (espejo)."""
        rows = mirror(FLAT + [DROP, Z1, Z2, FAKE, INSIDE, BREAK])
        sig, _ = run(rows)
        s = at_zone(sig, Z0, SELL)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].vela0_index, len(rows) - 1)

    def test_tc04_operacion_real_flipx4(self):
        """TC-04 C1306-P02: 04:05 cierra dentro (78451) y no confirma; 04:10 (O 78453, C 78472) es la vela 0.
        Precios de la ventana de datos y del historial; el resto, reconstruido del fotograma 00m44s_extra."""
        t = lambda h, m: f"{h:02d}:{m:02d}"
        flat = [(78600, 78620, 78580, 78600)] * 20
        rows = flat + [(78600, 78605, 78400, 78410),                        # caída
                       (78410, 78440, 78350, 78430), (78430, 78456, 78360, 78380),
                       (78380, 78420, 78336, 78400), (78400, 78445, 78370, 78390),  # zona: 78336-78456
                       (78390, 78395, 78270, 78290), (78290, 78330, 78260, 78320),  # engaño (2 velas)
                       (78320, 78390, 78310, 78380), (78380, 78425, 78370, 78420),
                       (78420, 78445, 78400, 78440), (78440, 78455, 78430, 78451),  # 04:05 dentro
                       (78453, 78475, 78445, 78472)]                                 # 04:10 vela 0
        # La zona empieza a las 03:20, así la vela de cierre 78451 cae a las 04:05 (en la Rev. 0 de esta prueba
        # las horas iban desplazadas una vela: la de 78451 quedaba etiquetada 04:10).
        times = [t(1, 0)] * 21 + [t(3, 20 + 5 * i) if 20 + 5 * i < 60 else t(4, 20 + 5 * i - 60)
                                  for i in range(len(rows) - 21)]
        candles = [Candle(times[i], *r) for i, r in enumerate(rows)]
        sig, _ = detect(candles, Params(max_width=3.0, max_total=14, avg_n=20, wick="b"))
        s = at_zone(sig, 21)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].vela0.time, "04:10")
        self.assertEqual((s[0].level_low, s[0].level_high), (78336, 78456))
        # Ventana de salida (FR-30): vela 4 = 04:30, cierra a las 04:35.
        self.assertEqual(4 * 60 + 10 + 5 * 5, 4 * 60 + 35)

    def test_tc06_verde_larga_cierra_dentro(self):
        """TC-06/TC-07 C1306-P08 @ 01:13-01:44, E2-08 @ 00:47-01:00: la verde larga cierra dentro; confirma la siguiente."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, (106, 118.5, 100.5, 118), BREAK]
        sig, _ = run(rows)
        self.assertEqual([s.vela0_index for s in at_zone(sig, Z0)], [len(rows) - 1])

    def test_tc08_rsr_engano_por_mecha(self):
        """TC-05/TC-08 C1306-P04, C1306-P05 @ 01:34-01:44: venta con engaño solo de mecha."""
        rows = mirror(FLAT + [DROP, Z1, Z2, (108, 110, 102, 107), INSIDE, BREAK])
        sig, _ = run(rows)
        self.assertEqual(len(at_zone(sig, Z0, SELL)), 1)

    def test_tc09_niveles_de_velas_distintas(self):
        """TC-09 C0907-P04 @ 00:14-00:29: alto de la 1.ª vela, bajo de la 4.ª (no contiguas)."""
        zone = [(110, 119, 108, 112), (112, 115, 109, 113), (113, 116, 108.5, 111), (111, 114, 104, 112)]
        rows = FLAT + [DROP] + zone + [(112, 113, 99, 106), INSIDE, BREAK]
        # Se comprueba la zona de 4 velas (Z0..Z0+3). La serie contiene además otro patrón válido anidado
        # (zona de 3 velas, engaño = 4.ª vela + la de 99) que con S-9 también confirma; no es el caso medido.
        # Con S-10 ambas zonas confirman en la misma vela 0 y quedan en una sola señal: se mira la zona de 4 velas.
        z4 = lambda sig: [z for s in at_zone(sig, Z0) for z in s.zones if (z["start"], z["end"]) == (Z0, Z0 + 3)]
        s = z4(run(rows)[0])
        self.assertEqual((len(s), s[0]["levels"]), (1, "distintas"))
        self.assertEqual(z4(run(rows, replace(P, distinct_levels=False))[0]), [])


class ParameterCases(unittest.TestCase):
    def test_tc10_engano_de_tres_velas(self):
        """Mecanismo de P-4 con un engaño sintético de 3 velas: P-4 = 2 descarta; 3 y 4 dan compra.
        Se diseñó a partir de "tres-cuatro velas" (C1306-P09 @ 00:00-00:21), pero con las velas reales T-29 tiene
        4 velas de engaño: esa comprobación está en test_real_data.test_tc10_con_velas_reales_t29 (D-017)."""
        # Las 3 velas de engaño cierran fuera (por debajo de 104). Con S-9 una vela que cierra dentro ya es vuelta,
        # no engaño; la versión anterior tenía la 3.ª cerrando en 105 (dentro).
        rows = FLAT + [DROP, Z1, Z2, FAKE, (106, 108, 100, 103), (103, 104.5, 101, 102), INSIDE, BREAK]
        sig, dis = run(rows)
        self.assertEqual(at_zone(sig, Z0), [])
        self.assertIn("engaño > P-4", [d.reason for d in at_zone(dis, Z0)])
        for n in (3, 4):
            sig, _ = run(rows, replace(P, max_fake=n))
            self.assertEqual(len(at_zone(sig, Z0)), 1)

    def test_tc11_zona_muy_amplia(self):
        """TC-11 C1306-P05 @ 01:14-01:34: con tope de anchura la zona no se forma; sin tope, señal."""
        rows = FLAT + [DROP, (110, 150, 104, 140), (140, 152, 105, 108), FAKE, INSIDE, (116, 150, 115, 149),
                       (149, 154, 140, 153)]
        sig, _ = run(rows)
        self.assertEqual(at_zone(sig, Z0), [])
        sig, _ = run(rows, replace(P, max_width=4.0))   # cabe la zona (≈3,3 velas medias), no la caída
        self.assertEqual(len(at_zone(sig, Z0)), 1)

    def test_tc12_consolidacion_f6(self):
        """TC-12 E2-05 @ 05:44-06:20: zona con cierres que cruzan la mitad varias veces; F-6 la descarta."""
        zone = [(110, 119, 104, 117), (117, 118, 105, 106), (106, 118, 105, 117), (117, 118, 105, 106),
                (106, 118, 105, 116)]
        rows = FLAT + [DROP] + zone + [FAKE, INSIDE, BREAK]
        p = replace(P, max_total=12)
        sig, _ = run(rows, p)
        self.assertEqual(len(at_zone(sig, Z0)), 1)
        self.assertEqual(at_zone(sig, Z0)[0].measures["F6_crossings"], 4)
        sig, dis = run(rows, replace(p, f6_max_crossings=2))
        self.assertEqual(at_zone(sig, Z0), [])
        self.assertIn("filtro F-6", [d.reason for d in at_zone(dis, Z0)])

    def test_tc13_vela_de_ruptura_muy_larga(self):
        """TC-13 C1306-P06 @ 01:07-01:17: con F-2 se descarta; sin filtro, señal."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, (116, 170, 115, 168)]
        sig, _ = run(rows)
        self.assertEqual(len(at_zone(sig, Z0)), 1)
        sig, dis = run(rows, replace(P, f2_max_vela0=2.0))
        self.assertEqual(at_zone(sig, Z0), [])

    def test_tc14_obstaculo_cercano(self):
        """TC-14 C0907-P11 @ 00:39-00:52: F-5 descarta si el obstáculo previo está demasiado cerca."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, BREAK]
        sig, _ = run(rows)
        room = at_zone(sig, Z0)[0].measures["F5_room"]
        self.assertIsNotNone(room)
        self.assertEqual(at_zone(run(rows, replace(P, f5_min_room=room + 1))[0], Z0), [])
        self.assertEqual(len(at_zone(run(rows, replace(P, f5_min_room=room - 1))[0], Z0)), 1)

    def test_tc15_rechazo(self):
        """TC-15 C0907-P11 @ 01:48-01:55: ruptura con mecha de rechazo; F-4 la descarta."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, (116, 140, 115, 121)]
        self.assertEqual(len(at_zone(run(rows)[0], Z0)), 1)
        self.assertEqual(at_zone(run(rows, replace(P, f4_max_rejection=0.5))[0], Z0), [])

    def test_tc17_sin_caida_previa_f1(self):
        """TC-17 C1306-P03 @ 02:21-02:49: SRS sin caída previa; F-1 lo descarta."""
        flat = [(112, 117, 107, 112)] * 20
        rows = flat + [Z1, Z2, FAKE, INSIDE, BREAK]
        p = replace(P, max_total=40, max_width=3.0)
        sig, _ = run(rows, p)
        self.assertTrue(sig)
        self.assertLess(sig[-1].measures["F1_prior_move"], 3)
        sig, _ = run(rows, replace(p, f1_min_prior=3))
        self.assertEqual([s for s in sig if s.direction == BUY], [])

    def test_tc18_19_19b_mecha_lado_entrada(self):
        """TC-18 C0907-P10 (a), TC-19 C1306-P03 (b), TC-19b C1306-P06 @ 00:17-00:27 (c, lectura de R-34)."""
        wick = (106, 121, 105, 116)            # mecha por encima de 119, cierra dentro
        mid = (116, 120.5, 115, 120)            # cierra entre 119 y 121
        rows = FLAT + [DROP, Z1, Z2, FAKE, wick, mid, BREAK]
        self.assertEqual(at_zone(run(rows, replace(P, wick="a"))[0], Z0), [])
        s = at_zone(run(rows, replace(P, wick="b"))[0], Z0)
        self.assertEqual((len(s), s[0].vela0_index), (1, len(rows) - 2))     # en "b" confirma la de 120
        s = at_zone(run(rows, replace(P, wick="c"))[0], Z0)
        self.assertEqual((len(s), s[0].vela0_index, s[0].entry_level), (1, len(rows) - 1, 121))


class ZoneChoice(unittest.TestCase):
    """D-017: la zona deja sitio para el engaño máximo y, si se descarta por duración, se prueba una más corta."""
    # 4 velas en 104-119; mínimos que no perforan los anteriores, para que no haya patrones anidados
    ZONE4 = [(112, 118, 104, 110), (110, 117, 104.5, 115), Z1, Z2]

    def test_reserva_para_el_engano(self):
        rows = FLAT + [DROP] + self.ZONE4 + [FAKE, (106, 108, 100, 103), INSIDE, BREAK]
        p = replace(P, max_total=9, max_fake=2)      # zona máx. = 9 - 2 - 2 = 5 velas
        sig, _ = run(rows, p)
        s = at_zone(sig, Z0)
        self.assertEqual((len(s), s[0].zone_end - s[0].zone_start + 1, s[0].fake_candles), (1, 4, 2))

    def test_reintento_con_zona_mas_corta(self):
        rows = FLAT + [DROP] + self.ZONE4 + [FAKE] + [INSIDE] * 4 + [BREAK]
        d = Detector(replace(P, max_total=10))        # zona de 4: 4+1+4+1 = 10 ok; se fuerza con 5 dentro
        for c in build(FLAT + [DROP] + self.ZONE4 + [FAKE] + [INSIDE] * 5 + [BREAK]):
            d.update(c)
        self.assertTrue(any("se prueba la zona más corta" in x.reason for x in d.discards))
        self.assertTrue(d.retries)
        s = [x for x in d.signals if x.direction == BUY and x.retried_from == (Z0, Z0 + 3)]
        self.assertEqual(len(s), 1)
        self.assertEqual((s[0].zone_start, s[0].total_candles), (Z0 + 1, 10))
        sig, _ = run(rows, replace(P, max_total=10))  # sin exceso: la zona de 4 confirma sin reintento
        self.assertEqual([x.retried_from for x in at_zone(sig, Z0)], [None])


class NoSignalCases(unittest.TestCase):
    def test_tc20_una_sola_vela_cruza_los_dos_niveles(self):
        """TC-20 C1306-P03 @ 00:09-00:41: sin señal ('no tomen eso')."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, (106, 125, 100, 124)]
        sig, dis = run(rows)
        self.assertEqual(at_zone(sig, Z0), [])
        self.assertIn("una sola vela cruza los dos niveles (R-28)", [d.reason for d in at_zone(dis, Z0)])

    def test_p9_vela_dentro_entre_engano_y_vela0(self):
        """P-9: sin vela que cierre dentro, (a) descarta; (b) da señal."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, BREAK]
        self.assertEqual(at_zone(run(rows)[0], Z0), [])
        self.assertEqual(len(at_zone(run(rows, replace(P, single_candle="vela0"))[0], Z0)), 1)

    def test_tc21_entra_pero_no_cierra_fuera(self):
        """TC-21 C1306-P06 @ 00:41-00:46: sin confirmación mientras no cierre fuera."""
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, (116, 118.9, 112, 118.9)]
        self.assertEqual(at_zone(run(rows)[0], Z0), [])

    def test_tc22_24_ruptura_sin_engano(self):
        """TC-22/TC-24 (S-3): ruptura por el lado de entrada sin engaño: sin SRS."""
        rows = FLAT + [DROP, Z1, Z2, INSIDE, BREAK]
        sig, _ = run(rows)
        self.assertEqual([s for s in sig if s.direction == BUY], [])

    def test_tc23_tope_de_duracion_total(self):
        """TC-23: el patrón supera P-5 y se descarta."""
        rows = FLAT + [DROP, Z1, Z2, FAKE] + [INSIDE] * 8 + [BREAK]
        sig, dis = run(rows)
        self.assertEqual(at_zone(sig, Z0), [])
        self.assertIn("duración total > P-5", [d.reason for d in at_zone(dis, Z0)])


def random_walk(n, seed):
    rnd, price, rows = random.Random(seed), 1000.0, []
    for _ in range(n):
        o = price
        c = o + rnd.gauss(0, 5)
        rows.append((o, max(o, c) + abs(rnd.gauss(0, 3)), min(o, c) - abs(rnd.gauss(0, 3)), c))
        price = c
    return build(rows)


class Properties(unittest.TestCase):
    P = Params(max_width=3.0, max_total=12, avg_n=20, wick="b", max_fake=3)

    def test_tc25_causalidad(self):
        """TC-25: añadir velas futuras no cambia lo ya detectado."""
        candles = random_walk(1500, 7)
        full, _ = detect(candles, self.P)
        for cut in (300, 777, 1200):
            part, _ = detect(candles[:cut], self.P)
            self.assertEqual([(s.direction, s.zone_start, s.vela0_index) for s in part],
                             [(s.direction, s.zone_start, s.vela0_index) for s in full if s.vela0_index < cut])

    def test_tc26_una_senal_por_zona_y_paralelo(self):
        """TC-26: cada zona da como máximo una señal; hay candidatos vigilados en paralelo."""
        candles = random_walk(1500, 11)
        d, most = Detector(self.P), 0
        for c in candles:
            d.update(c)
            most = max(most, len(d.active))
        keys = [(s.direction, z["start"], z["end"]) for s in d.signals for z in s.zones]
        self.assertEqual(len(keys), len(set(keys)))
        groups = [(s.direction, s.vela0_index) for s in d.signals]       # S-10: una señal por vela 0 y dirección
        self.assertEqual(len(groups), len(set(groups)))
        self.assertGreaterEqual(most, 2)
        rows = FLAT + [DROP, Z1, Z2, FAKE, INSIDE, BREAK, (125, 126, 110, 112), (112, 118, 110, 116), BREAK]
        self.assertEqual(len(at_zone(run(rows)[0], Z0)), 1)

    def test_invariantes(self):
        """Toda señal cumple la estructura (sobre serie aleatoria)."""
        sig, _ = detect(random_walk(3000, 3), self.P)
        self.assertTrue(sig)
        for s in sig:
            buy = s.direction == BUY
            self.assertTrue(s.vela0.close > s.entry_level if buy else s.vela0.close < s.entry_level)
            self.assertGreaterEqual(s.zone_end - s.zone_start + 1, 2)
            self.assertLessEqual(s.fake_candles, self.P.max_fake)
            self.assertLessEqual(s.total_candles, self.P.max_total)
            self.assertLessEqual(s.width, self.P.max_width)
            self.assertGreaterEqual(s.inside_candles, 1)


if __name__ == "__main__":
    unittest.main()

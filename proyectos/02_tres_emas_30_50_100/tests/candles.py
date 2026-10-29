"""Fabrica velas inventadas para las pruebas (sin MT5)."""
import pandas as pd

from emas.indicators import ema


class Velas:
    """Construye una serie vela a vela; permite consultar las EMAs de la última vela."""

    def __init__(self, inicio=1000.0):
        self.o, self.h, self.l, self.c = [], [], [], []
        self.vela(inicio)

    def __len__(self):
        return len(self.c)

    @property
    def ultimo(self):
        return self.c[-1]

    def vela(self, close, open=None, high=None, low=None, mecha=0.3):
        """Añade una vela. Por defecto abre en el cierre anterior con mechas de 0,3."""
        if open is None:
            open = self.c[-1] if self.c else close
        self.o.append(open)
        self.c.append(close)
        self.h.append(max(open, close) + mecha if high is None else high)
        self.l.append(min(open, close) - mecha if low is None else low)
        return len(self.c) - 1

    def tendencia(self, n, paso, mecha=0.3):
        for _ in range(n):
            self.vela(self.ultimo + paso, mecha=mecha)
        return len(self.c) - 1

    def ema_actual(self, periodo):
        """EMA de la última vela (depende solo de los cierres)."""
        return ema(self.c, periodo)[-1]

    def poner_minimo(self, i, valor):
        self.l[i] = valor

    def df(self):
        return pd.DataFrame({"open": self.o, "high": self.h, "low": self.l, "close": self.c})


def espejo(df):
    """Refleja las velas (compra <-> venta): precio -> K - precio."""
    K = float(df["high"].max() + df["low"].min())
    return pd.DataFrame({"open": K - df["open"], "high": K - df["low"],
                         "low": K - df["high"], "close": K - df["close"]})


def preambulo(v, bajada=520, subida=160):
    """Bajada y luego subida: las EMAs se cruzan después del calentamiento y quedan
    alineadas al alza y separadas."""
    v.tendencia(bajada, -0.5)
    v.tendencia(subida, +0.5)


def patron_compra(v, toque="e30", maximo_rojo=False, confirmacion="encima",
                  velas_entre_ruptura_y_retesteo=1, ruptura_en_zona=False,
                  sin_retesteo=False):
    """Añade un patrón de compra como el de la imagen y devuelve las velas clave.

    toque: "e30" (mecha a la EMA 30), "e50" (llega a la EMA 50), "e100" (llega a la 100).
    confirmacion: "encima", "dentro", "debajo" (cierra bajo la zona) o "toca_e30".
    """
    v.tendencia(5, +1.0)  # impulso
    if maximo_rojo:
        apertura = v.ultimo + 1.6
        m = v.vela(v.ultimo + 1.0, open=apertura, high=apertura + 1.0)
    else:
        m = v.vela(v.ultimo + 1.0, high=v.ultimo + 2.0)
    techo, suelo = v.h[m], max(v.o[m], v.c[m])

    # Primer retroceso: 3 velas bajando; la tercera toca la EMA indicada.
    v.vela(v.ultimo - 2.5)
    v.vela(v.ultimo - 2.5)
    t = v.vela(v.ultimo - 2.5)
    assert all(v.l[k] > ema(v.c, 30)[k] for k in range(m, t)), "toque antes de lo previsto"
    nivel = {"e30": 30, "e50": 50, "e100": 100}[toque]
    v.poner_minimo(t, v.ema_actual(nivel) - 0.1)

    # Vuelve a subir hasta cerrar por encima del techo de la zona.
    while v.ultimo <= techo:
        b = v.vela(v.ultimo + 2.0)
    if ruptura_en_zona:
        v.poner_minimo(b, techo - 0.4)  # la vela de ruptura también toca la zona
    if sin_retesteo:
        v.tendencia(15, +1.0)
        return dict(maximo=m, toque=t, ruptura=b, techo=techo, suelo=suelo)
    # Velas entre la ruptura y el retesteo: suben poco para que la EMA 30 no alcance la zona.
    v.tendencia(velas_entre_ruptura_y_retesteo, +1.0 if velas_entre_ruptura_y_retesteo == 1 else +0.3)

    # Segundo retroceso: la vela de confirmación toca la zona.
    abre = v.ultimo
    if confirmacion == "encima":
        k = v.vela(techo + 0.5, open=abre, low=techo - 0.4)
    elif confirmacion == "dentro":
        k = v.vela(techo - 0.2, open=abre, low=techo - 0.4)
    elif confirmacion == "debajo":
        k = v.vela(suelo - 0.2, open=abre, low=suelo - 0.5)
    elif confirmacion == "toca_e30":
        k = v.vela(techo + 0.5, open=abre)
        v.poner_minimo(k, v.ema_actual(30) - 0.1)
    if confirmacion != "toca_e30":
        assert v.l[k] > v.ema_actual(30), "la confirmación tocaría la EMA 30"
    v.tendencia(6, +0.5)  # velas posteriores (salida en la 4.ª)
    return dict(maximo=m, toque=t, ruptura=b, confirmacion=k, techo=techo, suelo=suelo)

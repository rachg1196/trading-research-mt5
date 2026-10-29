# -*- coding: utf-8 -*-
"""Motor comun: carga de datos (solo DESARROLLO), armado de temporalidades, costes y hora de Ecuador."""
import numpy as np, pandas as pd

TFS = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30",
       "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1"]
MIN = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M6": 6, "M10": 10, "M12": 12, "M15": 15, "M20": 20, "M30": 30,
       "H1": 60, "H2": 120, "H3": 180, "H4": 240, "H6": 360, "H8": 480, "H12": 720, "D1": 1440}
TZ_SERVIDOR = "Europe/Athens"   # Weltrade: UTC+2 invierno / UTC+3 verano (cambios de hora europeos, verificado en huecos de M1)
TZ_ECUADOR = "America/Guayaquil"


def cargar_m1(ruta, desde, hasta, ajustar_splits=False):
    """Carga M1 y se queda SOLO con [desde, hasta). hasta = inicio de la reserva."""
    df = pd.read_csv(ruta, usecols=["time", "open", "high", "low", "close", "spread"])
    df["spread"] = df["spread"].astype(float)
    if ajustar_splits:
        # splits de acciones: salto de precio > 40% entre velas seguidas -> se ajustan los precios ANTERIORES
        r = df.open.iloc[1:].to_numpy() / df.close.iloc[:-1].to_numpy()
        for k in np.nonzero((r < 0.6) | (r > 1.6))[0]:
            df.loc[:k, ["open", "high", "low", "close", "spread"]] *= r[k]
    df = df[(df.time >= int(pd.Timestamp(desde).timestamp())) & (df.time < int(pd.Timestamp(hasta).timestamp()))]
    df = df.reset_index(drop=True)
    df["dt"] = pd.to_datetime(df.time, unit="s")
    return df


def armar_tf(m1, tf):
    """Velas de la temporalidad a partir de M1 (verificado: identicas a las de MT5)."""
    if tf == "M1":
        out = m1[["dt", "open", "high", "low", "close", "spread"]].copy()
    else:
        out = (m1.set_index("dt").resample(f"{MIN[tf]}min", label="left", closed="left")
               .agg({"open": "first", "high": "max", "low": "min", "close": "last", "spread": "max"})
               .dropna().reset_index())
    out["time"] = out.dt.values.astype("datetime64[s]").astype("int64")
    return out.reset_index(drop=True)


def hora_ecuador(t_servidor_seg):
    """Convierte segundos 'hora servidor' a hora de Ecuador (serie datetime)."""
    s = pd.to_datetime(pd.Series(t_servidor_seg), unit="s")
    return s.dt.tz_localize(TZ_SERVIDOR, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert(TZ_ECUADOR).dt.tz_localize(None)

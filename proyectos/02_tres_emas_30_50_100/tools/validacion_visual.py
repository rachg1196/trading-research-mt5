"""Paso previo 1.b (BACKTEST_PLAN §1): imágenes de señales y de patrones anulados, para revisar a ojo.

Solo usa el periodo de DESARROLLO: cada serie se corta antes de la fecha de reserva del manifiesto,
así que el detector nunca ve la reserva. No calcula ni muestra resultados (ni ganancia ni pérdida).

Elige al azar (semilla "imagenes_validacion" del manifiesto) combinaciones símbolo × temporalidad,
con un máximo de 2 por símbolo y 2 por temporalidad, y de cada una toma una señal al azar, alternando
compras y ventas. Además toma 5 patrones anulados, con motivos distintos cuando es posible.

Salida: analysis/validacion/imagenes/01..20.png (señales), A1..A5.png (anulados),
A5_corregida.png (tramo de la antigua A5 con el detector corregido, D-021) e indice.csv.
Uso:  python tools\\validacion_visual.py
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from emas.detector import detectar  # noqa: E402
from emas.indicators import ema  # noqa: E402

HIST = RAIZ / "analysis" / "mt5" / "history"
MANIFIESTO = RAIZ / "analysis" / "backtest" / "manifiesto.json"
SALIDA = RAIZ / "analysis" / "validacion" / "imagenes"

N_SENALES, N_ANULADOS = 20, 5
MAX_POR_SIMBOLO, MAX_POR_TF = 2, 2
VELAS_ANTES, VELAS_DESPUES = 80, 6

# Colores como el gráfico de referencia.
FONDO, VERDE, ROJA, MECHA = "#8c8c8c", "#1f9d3a", "#e0201b", "#202020"
COLOR_EMA = {30: "#ffffff", 50: "#f2e600", 100: "#000000"}
ZONA = "#4a78d8"

MOTIVOS = {
    "cierre por debajo de la zona": "Cerró por debajo de la zona",
    "toco la EMA 100": "Tocó la EMA 100",
    "segundo retroceso toco la EMA 30": "En el segundo retroceso tocó la EMA 30",
    "P-11 EMAs sin orden o sin separacion": "EMAs sin orden o pegadas (P-11)",
    "P-08 maximo demasiado lejos del toque": "Máximo demasiado lejos del toque (P-08)",
    "P-09 sin ruptura a tiempo": "Sin ruptura a tiempo (P-09)",
    "P-09 ruptura demasiado tarde": "Ruptura demasiado tarde (P-09)",
    "P-10 sin confirmacion a tiempo": "Sin confirmación a tiempo (P-10)",
    "P-13 zona sin altura": "Zona sin altura (P-13)",
    "P-02 cruce demasiado reciente": "EMAs recién cruzadas en la confirmación (P-02)",
}

# Imagen extra (D-021): mismo tramo que la antigua A5, con el detector corregido.
EXTRA_A5 = {"simbolo": "FlipX 2", "tf": "H3", "centro": "2024-06-21 21:00",
            "desde": "2024-06-20 00:00", "hasta": "2024-06-21 21:00"}


def cargar_desarrollo(serie):
    df = pd.read_csv(HIST / serie["archivo"])
    df = df[pd.to_datetime(df["time"]) < pd.Timestamp(serie["corte_reserva"])]
    return df.reset_index(drop=True)


def patrones_anulados(eventos, direccion):
    """Reconstruye los patrones anulados a partir del registro de eventos del detector."""
    anulados, actual = [], None
    for i, tipo, info in eventos:
        if tipo == "toque_ema30":
            actual = {"direccion": direccion, "vela_toque": i,
                      "vela_maximo": int(info.split("=")[1]), "vela_ruptura": None}
        elif tipo == "ruptura" and actual:
            actual["vela_ruptura"] = i
        elif tipo == "senal":
            actual = None
        elif tipo == "anulado" and actual:
            actual.update(vela_anulado=i, motivo=info)
            anulados.append(actual)
            actual = None
    return anulados


def zona(df, m, direccion):
    o, h, l, c = (df[k].iloc[m] for k in ("open", "high", "low", "close"))
    return (max(o, c), h) if direccion == "compra" else (l, min(o, c))


def dibujar(df, titulo, direccion, marcas, vela_centro, zona_baja, zona_alta, archivo, motivo=None):
    ini = max(0, vela_centro - VELAS_ANTES)
    fin = min(len(df) - 1, vela_centro + VELAS_DESPUES)
    x = np.arange(ini, fin + 1)
    o, h, l, c = (df[k].to_numpy()[ini:fin + 1] for k in ("open", "high", "low", "close"))

    fig, ax = plt.subplots(figsize=(13, 7), dpi=110)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    for n in (100, 50, 30):  # EMAs sobre TODO el historial cargado, como el detector
        ax.plot(x, ema(df["close"], n)[ini:fin + 1], color=COLOR_EMA[n], lw=1.4, label=f"EMA {n}")
    for k, xi in enumerate(x):
        color = VERDE if c[k] >= o[k] else ROJA
        ax.vlines(xi, l[k], h[k], color=MECHA, lw=0.9, zorder=2)
        ax.add_patch(Rectangle((xi - 0.35, min(o[k], c[k])), 0.7, max(abs(c[k] - o[k]), 1e-9),
                               facecolor=color, edgecolor=MECHA, lw=0.5, zorder=3))
    m = marcas["Máximo" if direccion == "compra" else "Mínimo"]
    ax.add_patch(Rectangle((m - 0.4, zona_baja), fin + 0.4 - (m - 0.4), zona_alta - zona_baja,
                           facecolor=ZONA, edgecolor=ZONA, alpha=0.45, zorder=1))

    rango = h.max() - l.min()
    for k, (etiqueta, xi) in enumerate(marcas.items()):
        if xi is None or not ini <= xi <= fin:
            continue
        j = xi - ini
        arriba = (direccion == "compra") == (etiqueta in ("Máximo", "Ruptura", "Salida", "Anulado"))
        if etiqueta == "Mínimo":
            arriba = False
        y = h[j] if arriba else l[j]
        dy = (0.06 + 0.035 * (k % 3)) * rango * (1 if arriba else -1)
        ax.annotate(etiqueta, xy=(xi, y), xytext=(xi, y + dy), ha="center",
                    va="bottom" if arriba else "top", fontsize=9, fontweight="bold",
                    color="#7a0000" if etiqueta == "Anulado" else "#0b1f5c",
                    arrowprops=dict(arrowstyle="->", color="#0b1f5c", lw=1.1),
                    bbox=dict(boxstyle="round,pad=0.2", fc="#f4f4f4", ec="none", alpha=0.85), zorder=5)
    if motivo:
        ax.text(0.01, 0.97, f"ANULADO: {motivo}", transform=ax.transAxes, va="top", fontsize=12,
                fontweight="bold", color="#7a0000",
                bbox=dict(boxstyle="round,pad=0.3", fc="#f4f4f4", ec="#7a0000"), zorder=6)

    tiempos = df["time"].to_numpy()[ini:fin + 1]
    paso = max(1, len(x) // 8)
    ax.set_xticks(x[::paso])
    ax.set_xticklabels([t[5:16] for t in tiempos[::paso]], fontsize=8)
    ax.set_xlim(ini - 1, fin + 1)
    ax.margins(y=0.12)
    ax.grid(color="#9c9c9c", lw=0.5)
    ax.legend(loc="lower right" if direccion == "compra" else "upper right", facecolor=FONDO, fontsize=8)
    ax.set_title(titulo, fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


def imagen_extra_a5(manifiesto):
    """Dibuja el tramo de la antigua A5 y devuelve su fila del índice."""
    serie = next(s for s in manifiesto["series"]
                 if s["simbolo"] == EXTRA_A5["simbolo"] and s["tf"] == EXTRA_A5["tf"])
    df = cargar_desarrollo(serie)
    tiempos = pd.to_datetime(df["time"])
    centro = int(np.where(tiempos == pd.Timestamp(EXTRA_A5["centro"]))[0][0])
    dentro = lambda i: EXTRA_A5["desde"] <= df["time"].iloc[i][:16] <= EXTRA_A5["hasta"]
    senales, eventos = detectar(df, direccion="compra", con_eventos=True)
    anulado = next((a for a in patrones_anulados(eventos["compra"], "compra") if dentro(a["vela_toque"])),
                   None)
    senal = next((s for s in senales if dentro(s.vela_toque)), None)
    nombre = "A5_corregida"
    titulo = f"{nombre} · {EXTRA_A5['simbolo']} · {EXTRA_A5['tf']} · COMPRA · mismo tramo que la A5 antigua"
    if senal:
        marcas = {"Máximo": senal.vela_maximo, "Toque EMA": senal.vela_toque, "Ruptura": senal.vela_ruptura,
                  "Confirmación": senal.vela_confirmacion, "Entrada": senal.vela_entrada,
                  "Salida": senal.vela_salida}
        dibujar(df, titulo, "compra", marcas, centro, senal.zona_baja, senal.zona_alta,
                SALIDA / f"{nombre}.png")
        return [nombre, EXTRA_A5["simbolo"], EXTRA_A5["tf"], "compra", df["time"].iloc[centro],
                *(df["time"].iloc[k] for k in (senal.vela_maximo, senal.vela_toque, senal.vela_ruptura,
                                               senal.vela_confirmacion)), "SEÑAL"]
    a = anulado
    marcas = {"Máximo": a["vela_maximo"], "Toque EMA": a["vela_toque"], "Ruptura": a["vela_ruptura"],
              "Anulado": a["vela_anulado"]}
    motivo = MOTIVOS.get(a["motivo"], a["motivo"])
    dibujar(df, titulo, "compra", marcas, centro, *zona(df, a["vela_maximo"], "compra"),
            SALIDA / f"{nombre}.png", motivo=motivo)
    return [nombre, EXTRA_A5["simbolo"], EXTRA_A5["tf"], "compra", df["time"].iloc[a["vela_anulado"]],
            df["time"].iloc[a["vela_maximo"]], df["time"].iloc[a["vela_toque"]],
            "" if a["vela_ruptura"] is None else df["time"].iloc[a["vela_ruptura"]], "", motivo]


def main():
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    rng = np.random.default_rng(manifiesto["semillas"]["imagenes_validacion"])
    series = [s for s in manifiesto["series"] if s["estado"] == "ok"]
    orden = rng.permutation(len(series))
    SALIDA.mkdir(parents=True, exist_ok=True)

    senales, anulados = [], []
    por_simbolo, por_tf, motivos_usados = Counter(), Counter(), set()
    for idx in orden:
        if len(senales) >= N_SENALES and len(anulados) >= N_ANULADOS:
            break
        serie = series[idx]
        sym, tf = serie["simbolo"], serie["tf"]
        quiere_senal = (len(senales) < N_SENALES and por_simbolo[sym] < MAX_POR_SIMBOLO
                        and por_tf[tf] < MAX_POR_TF)
        if not quiere_senal and len(anulados) >= N_ANULADOS:
            continue
        df = cargar_desarrollo(serie)
        encontradas, eventos = detectar(df, con_eventos=True)
        # Solo señales cuya salida (confirmación + 4) también está en el desarrollo.
        encontradas = [s for s in encontradas if s.vela_salida + VELAS_DESPUES - 4 < len(df)]

        if quiere_senal and encontradas:
            compras = sum(s["direccion"] == "compra" for s in senales)
            preferida = "compra" if compras <= len(senales) - compras else "venta"
            candidatas = [s for s in encontradas if s.direccion == preferida] or encontradas
            s = candidatas[rng.integers(len(candidatas))]
            senales.append({"simbolo": sym, "tf": tf, "direccion": s.direccion,
                            "vela_maximo": s.vela_maximo, "vela_toque": s.vela_toque,
                            "vela_ruptura": s.vela_ruptura, "vela_confirmacion": s.vela_confirmacion,
                            "vela_entrada": s.vela_entrada, "vela_salida": s.vela_salida,
                            "zona": (s.zona_baja, s.zona_alta), "df": df})
            por_simbolo[sym] += 1
            por_tf[tf] += 1

        if len(anulados) < N_ANULADOS:
            todos = [a for d in ("compra", "venta") for a in patrones_anulados(eventos[d], d)
                     if a["vela_anulado"] + VELAS_DESPUES < len(df)]
            nuevos = [a for a in todos if a["motivo"] not in motivos_usados]
            if nuevos:
                a = nuevos[rng.integers(len(nuevos))]
                motivos_usados.add(a["motivo"])
                anulados.append({**a, "simbolo": sym, "tf": tf, "df": df,
                                 "zona": zona(df, a["vela_maximo"], a["direccion"])})

    filas = []
    for n, s in enumerate(senales, 1):
        df = s["df"]
        fecha = df["time"].iloc[s["vela_confirmacion"]]
        extremo = "Máximo" if s["direccion"] == "compra" else "Mínimo"
        marcas = {extremo: s["vela_maximo"], "Toque EMA": s["vela_toque"], "Ruptura": s["vela_ruptura"],
                  "Confirmación": s["vela_confirmacion"], "Entrada": s["vela_entrada"],
                  "Salida": s["vela_salida"]}
        titulo = f"{n:02d} · {s['simbolo']} · {s['tf']} · {s['direccion'].upper()} · {fecha}"
        dibujar(df, titulo, s["direccion"], marcas, s["vela_confirmacion"], *s["zona"],
                SALIDA / f"{n:02d}.png")
        filas.append([f"{n:02d}", s["simbolo"], s["tf"], s["direccion"], fecha,
                      *(df["time"].iloc[s[k]] for k in ("vela_maximo", "vela_toque", "vela_ruptura",
                                                       "vela_confirmacion")), ""])
    for n, a in enumerate(anulados, 1):
        df = a["df"]
        fecha = df["time"].iloc[a["vela_anulado"]]
        extremo = "Máximo" if a["direccion"] == "compra" else "Mínimo"
        marcas = {extremo: a["vela_maximo"], "Toque EMA": a["vela_toque"], "Ruptura": a["vela_ruptura"],
                  "Anulado": a["vela_anulado"]}
        motivo = MOTIVOS.get(a["motivo"], a["motivo"])
        titulo = f"A{n} · {a['simbolo']} · {a['tf']} · {a['direccion'].upper()} (anulado) · {fecha}"
        dibujar(df, titulo, a["direccion"], marcas, a["vela_anulado"], *a["zona"],
                SALIDA / f"A{n}.png", motivo=motivo)
        filas.append([f"A{n}", a["simbolo"], a["tf"], a["direccion"], fecha,
                      df["time"].iloc[a["vela_maximo"]], df["time"].iloc[a["vela_toque"]],
                      "" if a["vela_ruptura"] is None else df["time"].iloc[a["vela_ruptura"]],
                      "", motivo])
    filas.append(imagen_extra_a5(manifiesto))

    with (SALIDA / "indice.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["imagen", "simbolo", "tf", "direccion", "fecha", "vela_maximo", "vela_toque",
                    "vela_ruptura", "vela_confirmacion", "motivo_anulado"])
        w.writerows(filas)
    print(f"{len(senales)} señales y {len(anulados)} anulados en {SALIDA}")
    print("símbolos:", dict(por_simbolo))
    print("temporalidades:", dict(por_tf))
    print("compras/ventas:", Counter(s["direccion"] for s in senales))
    print("motivos anulados:", [MOTIVOS.get(a["motivo"], a["motivo"]) for a in anulados])


if __name__ == "__main__":
    main()

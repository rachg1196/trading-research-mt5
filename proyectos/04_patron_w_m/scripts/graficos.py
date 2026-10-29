# -*- coding: utf-8 -*-
"""Graficos estilo MT5 (fondo negro) de un patron detectado."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def dibujar(df, pat, titulo, ruta, antes=25, despues=40):
    i0 = max(0, int(pat["i_H0"]) - antes)
    i1 = min(len(df) - 1, int(pat["i_senal"]) + despues)
    sub = df.iloc[i0:i1 + 1]
    x = np.arange(len(sub))
    o, h, l, c = (sub[k].to_numpy() for k in ("open", "high", "low", "close"))

    fig, ax = plt.subplots(figsize=(12, 5.2), dpi=110)
    fig.patch.set_facecolor("black"); ax.set_facecolor("black")
    for xi, oi, hi, li, ci in zip(x, o, h, l, c):
        col = "#22c55e" if ci >= oi else "#e5e7eb"
        ax.vlines(xi, li, hi, color=col, lw=0.8)
        ax.add_patch(plt.Rectangle((xi - 0.35, min(oi, ci)), 0.7, max(abs(ci - oi), 1e-9),
                                   facecolor="black" if ci >= oi else col, edgecolor=col, lw=0.8))

    # zigzag del patron
    pts = [("H0", pat["i_H0"], pat["p_H0"]), ("1", pat["i_L1"], pat["p_L1"]),
           ("", pat["i_H1"], pat["p_H1"]), ("2", pat["i_L2"], pat["p_L2"])]
    if pat["toques"] == 3:
        pts += [("", pat["i_H2"], pat["p_H2"]), ("3", pat["i_L3"], pat["p_L3"])]
    zx = [int(p[1]) - i0 for p in pts]; zy = [p[2] for p in pts]
    ax.plot(zx, zy, color="#facc15", lw=2.2)
    es_w = pat["tipo"] == "W"
    for nombre, xi, yi in zip([p[0] for p in pts], zx, zy):
        if nombre in ("1", "2", "3"):
            ax.annotate(nombre, (xi, yi), textcoords="offset points",
                        xytext=(0, -16 if es_w else 10), ha="center", color="#facc15", fontsize=11, weight="bold")
    # cuello
    xs = int(pat["i_senal"]) - i0
    ax.hlines(pat["cuello"], zx[1], min(len(sub) - 1, xs + 15), color="#facc15", lw=1.4, ls="--")
    ax.annotate("cuello", (zx[1], pat["cuello"]), textcoords="offset points", xytext=(0, 5),
                color="#facc15", fontsize=9)
    # senal
    ax.scatter([xs], [c[xs]], marker="^" if es_w else "v", s=160,
               color="#3b82f6" if es_w else "#ef4444", zorder=5)
    ax.axvline(xs, color="#3b82f6" if es_w else "#ef4444", lw=0.8, alpha=0.6)

    ticks = np.linspace(0, len(sub) - 1, 8).astype(int)
    ax.set_xticks(ticks)
    ax.set_xticklabels([sub["time"].iloc[t].strftime("%d %b %H:%M") for t in ticks], color="#d1d5db", fontsize=8)
    ax.tick_params(axis="y", colors="#d1d5db", labelsize=8)
    ax.yaxis.tick_right()
    for s in ax.spines.values():
        s.set_color("#4b5563")
    ax.grid(color="#374151", ls=":", lw=0.6)
    ax.set_xlim(-1, len(sub))
    ax.set_title(titulo, color="white", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(ruta, facecolor="black")
    plt.close(fig)

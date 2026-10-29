import numpy as np, pandas as pd
from scipy import stats
d = pd.read_csv("datos/completo/Apple_M1.csv.gz", usecols=["time","open","high","low","close","spread"])
d["dt"] = pd.to_datetime(d.time, unit="s"); d["dia"] = d.dt.dt.normalize()
dia = d.groupby("dia").agg(open=("open","first"), close=("close","last"), n=("close","size"))
dia = dia[dia.n > 200]
# split adjust (ago-2020 4:1)
r = dia.open.values[1:] / dia.close.values[:-1]
for k in np.nonzero((r < 0.6) | (r > 1.6))[0]:
    dia.iloc[:k+1, :2] = dia.iloc[:k+1, :2] * r[k]
fechas = list(dia.index)
eventos = ["2020-06-22","2020-09-15","2020-10-13","2020-11-10","2021-04-20","2021-06-07","2021-09-14","2021-10-18",
           "2022-03-08","2022-06-06","2022-09-07","2023-06-05","2023-09-12","2023-10-30","2024-05-07","2024-06-10",
           "2024-09-09","2025-06-09","2025-09-09","2026-06-08","2026-09-09"]
resultados = ["2020-07-30","2020-10-29","2021-01-27","2021-04-28","2021-07-27","2021-10-28","2022-01-27","2022-04-28",
              "2022-07-28","2022-10-27","2023-02-02","2023-05-04","2023-08-03","2023-11-02","2024-02-01","2024-05-02",
              "2024-08-01","2024-10-31","2025-01-30","2025-05-01","2025-07-31","2025-10-30","2026-01-29","2026-04-30",
              "2026-07-30"]
COSTE = 0.26 / 347 * 100        # spread en % (~0,075 %)
def ret(i0, i1, campo0="close", campo1="close"):
    return (dia[campo1].iloc[i1] / dia[campo0].iloc[i0] - 1) * 100
ventanas = {
    "Comprar 5 dias antes y vender el dia antes (rumor)":      lambda i: ret(i-6, i-1),
    "Comprar 5 dias antes y vender al cierre del dia (rumor+noticia)": lambda i: ret(i-6, i),
    "Solo el dia del evento (apertura -> cierre)":               lambda i: ret(i, i, "open", "close"),
    "Despues: cierre del dia -> 5 dias despues":                 lambda i: ret(i, i+5),
    "Resultados: cierre del dia -> cierre del dia siguiente":    lambda i: ret(i, i+1),
}
N = len(fechas)
def tabla(lista, nombre):
    idx = [fechas.index(pd.Timestamp(f)) for f in lista if pd.Timestamp(f) in fechas]
    print(f"\n=== {nombre}: {len(idx)} fechas con datos ===")
    for vn, fn in ventanas.items():
        if "Resultados" in vn and "resultados" not in nombre.lower(): continue
        x = np.array([fn(i) for i in idx if 6 <= i < N - 6])
        todos = np.array([fn(i) for i in range(6, N - 6)])          # el mismo calculo en cualquier dia
        t, p = stats.ttest_ind(x, todos, equal_var=False)
        print(f"{vn:62s} | media {x.mean():+.2f}% | sube {100*(x>0).mean():3.0f}% | dia normal {todos.mean():+.2f}% (sube {100*(todos>0).mean():.0f}%) | "
              f"neto de spread {x.mean()-COSTE:+.2f}% | p={p:.2f}")
    return idx
tabla(eventos, "Eventos de producto (keynotes, WWDC)")
tabla(resultados, "Resultados trimestrales")
print("\nDetalle eventos: fecha | dia del evento | 5 dias antes->cierre | 5 dias despues")
for f in eventos:
    f = pd.Timestamp(f)
    if f in fechas:
        i = fechas.index(f)
        if 6 <= i < N-6: print(f.date(), f"{ret(i,i,'open','close'):+.2f}%", f"{ret(i-6,i):+.2f}%", f"{ret(i,i+5):+.2f}%")

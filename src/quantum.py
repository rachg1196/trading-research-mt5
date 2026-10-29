import numpy as np, pandas as pd
def senales(tfdf):
    c = tfdf.close.to_numpy(float)
    sma = pd.Series(c).rolling(55).mean().to_numpy()
    arriba = (c > sma).astype(float); arriba[np.isnan(sma)] = np.nan
    verde = pd.Series(arriba).rolling(12).sum().to_numpy(); roja = 12 - verde
    d = verde - roja
    compra = (d[1:] > 0) & (d[:-1] <= 0); venta = (d[1:] < 0) & (d[:-1] >= 0)
    i = np.arange(1, len(c))
    s = pd.DataFrame({"i": np.r_[i[compra], i[venta]], "tipo": np.r_[np.ones(compra.sum(), int), -np.ones(venta.sum(), int)]})
    return s.sort_values("i").reset_index(drop=True)

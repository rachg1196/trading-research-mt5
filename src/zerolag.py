import numpy as np, pandas as pd
def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()
def senales(tfdf, L=10):
    c = tfdf.close.to_numpy(float)
    e1 = ema(c, L); zl = ema(2 * c - e1, L)
    d = zl - e1; d[:2 * L] = np.nan
    compra = (d[1:] > 0) & (d[:-1] <= 0); venta = (d[1:] < 0) & (d[:-1] >= 0)
    i = np.arange(1, len(c))
    s = pd.DataFrame({"i": np.r_[i[compra], i[venta]], "tipo": np.r_[np.ones(compra.sum(), int), -np.ones(venta.sum(), int)]})
    return s.sort_values("i").reset_index(drop=True)

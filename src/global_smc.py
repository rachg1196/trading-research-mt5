import pandas as pd, glob, numpy as np, sys
carp, N0 = sys.argv[1], int(sys.argv[2])
t = pd.concat([pd.read_csv(f) for f in glob.glob(f"{carp}/smc_*.csv")])
t = t[t.ops.notna()]
N = N0 + len(t)
t = t.sort_values("p_normal").reset_index(drop=True)
t["p_holm"] = np.minimum(1, t.p_normal.fillna(1) * (N - np.arange(len(t)))).cummax()
t["bruto"] = t.usd_por_op + t.spread_usd
t["pasa"] = (t.ops>=30)&(t.usd_por_op>0)&(t.p_holm<0.05)&(t.anios_pos_frac>0.5)&(t.usd_por_op_spread15>0)
v = t[t.ops>=30]
print(len(t), "pruebas (", len(v), "con >=30 ops) | pasan:", t.pasa.sum(), "| positivas:", (v.usd_por_op>0).sum(),
      "| mejor que azar:", round((v.usd_por_op>v.azar_media).mean(),2), "| p<0.05 sin corregir:", (v.p_normal<0.05).sum(),
      "| esperadas por azar:", round(0.05*len(v)))
cols=["simbolo","tf","senal","filtro","salida","direccion","ops","aciertos_pct","usd_por_op","azar_media","p_normal","p_holm","anios_positivos","usd_por_op_spread15","ops_por_semana"]
print(v[cols].head(25).to_string())
print("\nMediana neto-azar por senal:"); print((v.usd_por_op - v.azar_media).groupby(v.senal).median().round(4))
print("\nMediana neto-azar por TF:"); print((v.usd_por_op - v.azar_media).groupby(v.tf).median().round(4))
print("\nFraccion mejor que azar por senal:"); print((v.usd_por_op > v.azar_media).groupby(v.senal).mean().round(2))
t.to_csv(f"{carp}/smc_global.csv", index=False)

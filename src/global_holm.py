import pandas as pd, glob, numpy as np
pd.set_option('display.width',250)
fs=[f for f in glob.glob('resultados/wm_*.csv') if 'todo' not in f and 'global' not in f]
t=pd.concat([pd.read_csv(f) for f in fs]); t=t[t.ops.fillna(0)>0].copy()
t['pp']=t['p_normal'].fillna(t['p'])
N=len(t); p=t.pp.to_numpy(); o=np.argsort(p); adj=np.empty(N); run=0
for r,i in enumerate(o): run=max(run,min(1,(N-r)*p[i])); adj[i]=run
t['p_holm']=adj
t['pasa']=(t.ops>=30)&(t.usd_por_op>0)&(t.p_holm<0.05)&(t.anios_pos_frac>0.5)&(t.usd_por_op_spread15>0)
t.to_csv('resultados/wm_global.csv',index=False)
print(N,'pruebas, simbolos',t.simbolo.nunique(),'pasan',int(t.pasa.sum()))
print(t.sort_values('pp').head(12)[['simbolo','tf','direccion','ops','usd_por_op','bruto_por_op','spread_por_op','pp','p_holm','anios_positivos','usd_por_op_spread15']].to_string())
print('celdas con neto>0:',(t.usd_por_op>0).sum(),'de',N, '| bruto medio global', round(t.bruto_por_op.mean(),4))

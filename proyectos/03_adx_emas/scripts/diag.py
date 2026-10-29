from bt import load
from ind import *
import numpy as np, pandas as pd
r=pd.read_pickle('base130.pkl')
d=load('M5'); h,l,c,o=d.high.values,d.low.values,d.close.values,d.open.values
t=d.time
e30,e50,e100=ema(c,30),ema(c,50),ema(c,100)
adx,pdi,ndi=adx_mt5(h,l,c,14)
tr=np.maximum.reduce([h-l,np.abs(h-np.r_[c[0],c[:-1]]),np.abs(l-np.r_[c[0],c[:-1]])])
atr=pd.Series(tr).rolling(14).mean().values*100
atr_d=pd.Series(tr).rolling(288).mean().values*100
up=(e30>e50)&(e50>e100); dn=(e30<e50)&(e50<e100)
st=np.where(up,1,np.where(dn,-1,0))
# bars since alignment & move since alignment
age=np.zeros(len(c)); mv=np.zeros(len(c)); start=0
for i in range(1,len(c)):
    if st[i]!=st[i-1]: start=i
    age[i]=i-start; mv[i]=(c[i]-c[start])*100*st[i]
pos=np.searchsorted(t.values,r.open.values)-1  # vela de señal
F=pd.DataFrame({'pts':r.pts.values,'side':r.side.values,'hora':r.open.dt.hour.values,'dow':r.open.dt.dayofweek.values,
 'adx':adx[pos],'atr':atr[pos],'atr_d':atr_d[pos],'edad':age[pos],'recorrido':mv[pos],
 'dist_e30':(c[pos]-e30[pos])*100*r.side.values,'sep':np.abs(e30[pos]-e100[pos])*100})
F.to_pickle('feat.pkl')
def tab(col,bins=None,q=5):
    x=F[col] if bins is None else pd.cut(F[col],bins)
    if bins is None and F[col].nunique()>24: x=pd.qcut(F[col],q,duplicates='drop')
    g=F.groupby(x,observed=True).pts.agg(['size','mean','sum'])
    g['se']=7100/np.sqrt(g['size']); g['z']=(g['mean']+124)/g.se  # vs azar (-124)
    print('\n==',col); print(g.round(1).to_string())
for col in ['hora','dow','adx','atr','atr_d','edad','recorrido','dist_e30','sep']: tab(col)
# market character
ret=np.diff(c)
for k in [1,3,12,48]:
    rk=c[k:]-c[:-k]
    print('autocorr retornos agregados',k, np.corrcoef(rk[:-k][::k],rk[k:][::k])[0,1].round(4))
for k in [3,12,48,288]:
    vr=np.var(c[k:]-c[:-k])/(k*np.var(ret)); print('variance ratio',k,round(vr,3))

import numpy as np, pandas as pd, sys
from ind import *
D='/mnt/user-data/uploads/proyecto adx emas/04_datos/'
def load(tf): return pd.read_csv(D+f'BreakX600_{tf}.csv',parse_dates=['time'])
m1=load('M1'); m1t=m1.time.values.astype('datetime64[s]').astype(np.int64)
H1=m1.high.values; L1=m1.low.values; C1=m1.close.values
def exit_scan(k,side,entry,sl,tp,spr,maxbars=50000):
    # k: index of first M1 bar; bid prices; buy closes at bid, sell at ask=bid+spr
    for j in range(k,min(k+maxbars,len(H1))):
        if side==1:
            hs=L1[j]<=sl; ht=H1[j]>=tp
        else:
            hs=H1[j]+spr>=sl; ht=L1[j]+spr<=tp
        if hs: return j,sl   # pesimista: SL primero si ambos
        if ht: return j,tp
    j=min(k+maxbars,len(H1))-1
    return j,(C1[j] if side==1 else C1[j]+spr)
def run(tf='M5',spread_pts=130,SLp=10000,TPp=5000,adxlvl=20,start='2025-01-01',end='2026-05-01',use_cci=True):
    d=load(tf); h,l,c,o=d.high.values,d.low.values,d.close.values,d.open.values
    e30,e50,e100=ema(c,30),ema(c,50),ema(c,100)
    adx,pdi,ndi=adx_mt5(h,l,c,14); cc=cci(h,l,c,14)
    up=(e30>e50)&(e50>e100); dn=(e30<e50)&(e50<e100)
    ccb=cc>-100 if use_cci else np.ones(len(c),bool); ccs=cc<100 if use_cci else np.ones(len(c),bool)
    sb=up&(adx>adxlvl)&(pdi>ndi)&ccb; ss=dn&(adx>adxlvl)&(ndi>pdi)&ccs
    t=d.time.values.astype('datetime64[s]').astype(np.int64)
    spr=spread_pts*0.01; SL=SLp*0.01; TP=TPp*0.01
    t0=pd.Timestamp(start).value//10**9; t1=pd.Timestamp(end).value//10**9
    trades=[]; bexe=sexe=False; bfree=sfree=-1
    idx=np.searchsorted(m1t,t)
    for i in range(300,len(c)):
        if t[i]<t0 or t[i]>=t1: continue
        sbi,ssi=sb[i-1],ss[i-1]   # vela cerrada
        for side,sig in ((1,sbi),(-1,ssi)):
            exe=bexe if side==1 else sexe; free=bfree if side==1 else sfree
            if sig:
                if (not exe) and t[i]>free:
                    if side==1: ent=o[i]+spr; sl=ent-SL; tp=ent+TP
                    else: ent=o[i]; sl=ent+SL; tp=ent-TP
                    j,px=exit_scan(idx[i],side,ent,sl,tp,spr)
                    pts=(px-ent)*side*100
                    trades.append((pd.Timestamp(t[i],unit='s'),side,ent,pd.Timestamp(m1t[j],unit='s'),px,pts))
                    if side==1: bexe=True; sexe=False; bfree=m1t[j]+59
                    else: sexe=True; bexe=False; sfree=m1t[j]+59
            else:
                if side==1: bexe=False
                else: sexe=False
    return pd.DataFrame(trades,columns=['open','side','entry','close','exit','pts'])

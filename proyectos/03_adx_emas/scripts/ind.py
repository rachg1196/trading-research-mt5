import numpy as np, pandas as pd
def ema(x,n):
    a=2/(n+1); out=np.empty(len(x)); out[0]=x[0]
    for i in range(1,len(x)): out[i]=out[i-1]+a*(x[i]-out[i-1])
    return out
def adx_mt5(h,l,c,n=14):
    ph=np.r_[h[0],h[:-1]]; pl=np.r_[l[0],l[:-1]]; pc=np.r_[c[0],c[:-1]]
    p=np.maximum(h-ph,0); m=np.maximum(pl-l,0)
    pp=np.where(p>m,p,0.0); mm=np.where(m>p,m,0.0)
    tr=np.maximum.reduce([h-l,np.abs(h-pc),np.abs(l-pc)])
    with np.errstate(divide='ignore',invalid='ignore'):
        pd_=np.where(tr!=0,100*pp/tr,0); nd=np.where(tr!=0,100*mm/tr,0)
    pdi=ema(pd_,n); ndi=ema(nd,n); s=pdi+ndi
    dx=np.where(s!=0,100*np.abs(pdi-ndi)/np.where(s==0,1,s),0)
    return ema(dx,n),pdi,ndi
def cci(h,l,c,n=14):
    tp=pd.Series((h+l+c)/3); sma=tp.rolling(n).mean()
    md=tp.rolling(n).apply(lambda x: np.abs(x-x.mean()).mean(),raw=True)
    return ((tp-sma)/(0.015*md)).values

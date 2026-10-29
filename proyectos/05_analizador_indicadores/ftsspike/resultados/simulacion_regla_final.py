import pandas as pd, numpy as np, sys
TP,SL,HOLD=5000,11000,60*24*2
m1=pd.read_csv('f2/velas_M1.csv'); t1=pd.to_datetime(m1.time,format='%Y.%m.%d %H:%M:%S').values
O=m1.open.values*100;H=m1.high.values*100;L=m1.low.values*100;SP=m1.spread.values.astype(float);N=len(m1)
v5=pd.read_csv('f2/velas_M5.csv').reset_index(drop=True); T5=pd.to_datetime(v5.time,format='%Y.%m.%d %H:%M:%S').values
idx5={t:i for i,t in enumerate(v5.time)}
f=pd.read_csv('fts/fts_tester_M5.csv').rename(columns={'shift':'sh'}); f=f[f.sh==10]   # EXACTAMENTE lo que se veia 10 velas despues
defin=sorted([(idx5[a],p,c) for a,p,c in zip(f.vela_flecha,f.precio,f.color) if a in idx5])
def lines_at(vis,col):
    pts=sorted([a for a in vis if a[2]==col])[-2:]
    if len(pts)<2 or pts[0][0]==pts[1][0]: return None
    (i1,p1,_),(i2,p2,_)=pts; return (i2,p2,(p2-p1)/(i2-i1))
def signals(k0,k1):
    sig=[]; used=set(); di=0; old=[]
    for k in range(200,min(k1,len(v5)-1)):
        while di<len(defin) and defin[di][0]<=k-10: old.append(defin[di]); di+=1
        if k<k0: continue
        for col in (1,0):
            ln=lines_at(old[-6:],col)
            if ln is None: continue
            i2,p2,m=ln
            if (col==1 and m>=0) or (col==0 and m<=0): continue      # variante del metodo de Raul (pendiente a favor)
            if (col,i2) in used: continue
            j=k+1; lv=(p2+m*(j-i2))*100; hi=v5.high[j]*100; lo=v5.low[j]*100; op=v5.open[j]*100
            if (hi>=lv and op<lv) if col==1 else (lo<=lv and op>lv):
                used.add((col,i2)); sig.append((T5[j],1 if col==1 else -1,lv))   # RUPTURA: toca linea de arriba -> compra
    return sig
def entry(t,side,lv):
    s=np.searchsorted(t1,t)
    for i in range(s,min(s+5,N)):
        if (side==1 and H[i]>=lv) or (side==-1 and L[i]<=lv): return i,(max(lv,O[i]) if side==1 else min(lv,O[i]))
    return -1,0
def trade(s,side,price,stop):
    end=min(stop,s+HOLD)
    if side==1: e=price+SP[s]; fav=np.r_[-1e9,H[s+1:end]-e]; adv=np.r_[e-L[s],e-L[s+1:end]]
    else: e=price; fav=np.r_[-1e9,e-(L[s+1:end]+SP[s+1:end])]; adv=np.r_[(H[s]+SP[s])-e,(H[s+1:end]+SP[s+1:end])-e]
    a=np.argmax(adv>=SL) if (adv>=SL).any() else 10**9; b=np.argmax(fav>=TP) if (fav>=TP).any() else 10**9
    if a<=b and a<10**9: return s+a,-max(adv[a],SL)
    if b<10**9: return s+b,TP
    k=end-1; return k,((O[k]-e) if side==1 else (e-O[k]-SP[k]))
def run(start,endt,nr=100,seed=1):
    k0=np.searchsorted(T5,np.datetime64(start)); k1=np.searchsorted(T5,np.datetime64(endt))
    i0=np.searchsorted(t1,np.datetime64(start)); i1=np.searchsorted(t1,np.datetime64(endt))
    S=[(*entry(t,sd,lv),sd) for t,sd,lv in signals(k0,k1)]; S=[(a,sd,px) for a,px,sd in S if 0<a<i1-1]
    R=np.array([trade(s,sd,lv,i1) for s,sd,lv in S]); p=R[:,1]
    rng=np.random.default_rng(seed); rand=[]
    for k in range(nr):
        rs=rng.integers(i0,i1-1,len(S)); rd=rng.choice([1,-1],len(S)); rand.append(np.mean([trade(a,b,O[a],i1)[1] for a,b in zip(rs,rd)]))
    rand=np.array(rand); days=(np.datetime64(endt)-np.datetime64(start)).astype('timedelta64[D]').astype(int)
    usd=p*0.001; cum=np.cumsum(usd); dd=(cum-np.maximum.accumulate(np.maximum(cum,0))).min()
    st=mx=0
    for x in p: st=st+1 if x<=0 else 0; mx=max(mx,st)
    mon=pd.Series(usd,index=pd.to_datetime(t1[[s for s,_,_ in S]]).to_period('M')).groupby(level=0).sum().round(2)
    return dict(ops=len(p),por_dia=round(len(p)/days,1),aciertos=round((p>0).mean()*100,1),gan_media=round(p[p>0].mean()),perd_media=round(p[p<=0].mean()),
        pts_op=round(p.mean(),1),neto_usd_lote01=round(usd.sum(),2),dd_usd=round(dd,2),peor_racha=mx,azar_p50=round(np.median(rand),1),
        azar_p95=round(np.percentile(rand,95),1),pct_vs_azar=round((rand<p.mean()).mean()*100),meses_pos=f'{(mon>0).sum()}/{len(mon)}',meses=mon.to_dict())
if __name__=='__main__':
    r=run(sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]))
    for k,v in r.items(): print(k,':',v)

from bt import *
import numpy as np, pandas as pd
r=pd.read_pickle('base130.pkl')
d=load('M5'); t=d.time.values.astype('datetime64[s]').astype(np.int64); o=d.open.values
idx=np.searchsorted(m1t,t)
spr=1.30; SL=100; TP=50
def outcome(i,side):
    ent=o[i]+spr if side==1 else o[i]
    sl=ent-SL*side; tp=ent+TP*side
    j,px=exit_scan(idx[i],side,ent,sl,tp,spr)
    return (px-ent)*side*100
pos=np.searchsorted(t,r.open.values.astype('datetime64[s]').astype(np.int64))
both=np.array([[outcome(i,1),outcome(i,-1)] for i in pos])
rng=np.random.default_rng(1)
N=2000
sims=np.array([both[np.arange(len(pos)),rng.integers(0,2,len(pos))].mean() for _ in range(N)])
# random times in dev period
t0=pd.Timestamp('2025-01-01').value//10**9; t1=pd.Timestamp('2026-05-01').value//10**9
cand=np.where((t>=t0)&(t<t1))[0][300:]
ri=rng.choice(cand,8000,replace=False)
rb=np.array([[outcome(i,1),outcome(i,-1)] for i in ri])
np.save('both.npy',both); np.save('rb.npy',rb)
sims2=np.array([rb[rng.choice(len(ri),len(pos)),rng.integers(0,2,len(pos))].mean() for _ in range(N)])
s=r.pts.mean()
print('estrategia media',round(s,1))
print('azar (mismas horas, dirección al azar) media',round(sims.mean(),1),'p5-p95',np.percentile(sims,[5,95]).round(1),'pct estrategia >= azar',(sims>=s).mean())
print('azar (horas y dirección al azar) media',round(sims2.mean(),1),'p5-p95',np.percentile(sims2,[5,95]).round(1),'p',(sims2>=s).mean())
print('mismas horas: dirección estrategia vs contraria', both[np.arange(len(pos)),(r.side.values==-1).astype(int)].mean(), both[np.arange(len(pos)),(r.side.values==1).astype(int)].mean())

import sys,numpy as np
exec(open('fts_tick_sim.py').read().split('A, B, D = [], [], []')[0])
rng=np.random.default_rng(7); n=188; res=[]
for rep in range(200):
    tt=rng.integers(t0,t1,n); dd=rng.choice([1,-1],n); v=[]
    for t,d in zip(tt,dd):
        k=np.searchsorted(ts,t); lv=bid[k]
        r,_=sim_ticks(int(ts[k]),d,lv)
        if r is not None: v.append(r*100)
    res.append(np.mean(v))
res=np.array(res); print(f"azar ticks: mediana {np.median(res):+.0f} p5 {np.percentile(res,5):+.0f} p95 {np.percentile(res,95):+.0f} | FTS +504 mejor que {np.mean(res<504.3)*100:.0f}%")

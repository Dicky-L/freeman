"""Five-year A-share signal study: no fake prices, fail closed when data unavailable."""
import argparse,json,time,random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import pandas as pd
import numpy as np

START,END,WARMUP="20211009","20261009","20210401"
COLS={"日期":"date","开盘":"open","最高":"high","最低":"low","收盘":"close","成交量":"volume","成交额":"amount"}
FIELDS=["symbol","signal_date","entry_date","entry_open","net_5d","net_10d","hit_3d_high_ge3pct","low_3d_drawdown","volume_ratio","relative_strength_5d"]
PREFIXES=("000","001","002","003","300","301","600","601","603","605")
def valid_symbol(x):
    x=str(x).zfill(6)
    return len(x)==6 and x.isdigit() and x.startswith(PREFIXES)
def universe(ak):
    f=ak.stock_info_a_code_name()
    c=next((c for c in ("code","代码","证券代码") if c in f),None)
    if not c: raise RuntimeError("No valid stock universe")
    codes=set(str(v).zfill(6) for v in f[c].dropna())
    delisted=0
    for name in ("stock_info_sh_delist","stock_info_sz_delist"):
        try:
            q=getattr(ak,name)()
            c=next((c for c in ("公司代码","证券代码","股票代码","代码","code") if c in q),None)
            if c:
                new=set(str(v).zfill(6) for v in q[c].dropna())
                delisted+=len(new-codes);codes.update(new)
        except Exception as e:print("DELIST_UNAVAILABLE",name,str(e)[:120],flush=True)
    return sorted(v for v in codes if valid_symbol(v)),delisted
def normalize(q):
    if q is None or q.empty:raise ValueError("empty")
    q=q.rename(columns=COLS).copy()
    needed=["date","open","high","low","close","volume","amount"]
    if any(c not in q for c in needed):raise ValueError("missing fields")
    q["date"]=pd.to_datetime(q["date"],errors="coerce")
    for c in needed[1:]:q[c]=pd.to_numeric(q[c],errors="coerce")
    q=q.dropna(subset=needed).sort_values("date").drop_duplicates("date")
    q=q[(q.open>0)&(q.high>=q.low)&(q.close>0)&(q.volume>0)&(q.amount>0)]
    if len(q)<150:raise ValueError("too few sessions")
    return q.reset_index(drop=True)
def fetch(code):
    import akshare as ak
    err=""
    for n in range(3):
        try:
            return code,normalize(ak.stock_zh_a_hist(symbol=code,period="daily",start_date=WARMUP,end_date=END,adjust="",timeout=15)),""
        except Exception as e:
            err=repr(e);time.sleep(.6*(n+1)+random.random()*.2)
    return code,None,err
def signals(code,f):
    g=f.copy()
    g["v20"]=g.volume.shift(1).rolling(20).mean()
    g["high20"]=g.high.shift(1).rolling(20).max()
    g["amount20"]=g.amount.shift(1).rolling(20).mean()
    g["r20"]=g.close/g.close.shift(20)-1
    g["r1"]=g.close/g.close.shift(1)-1
    items=[]
    for i in range(122,len(g)-11):
        b,p,t=g.iloc[i-2],g.iloc[i-1],g.iloc[i]
        if t.date<pd.Timestamp(START) or t.date>pd.Timestamp(END):continue
        if not (.02<=b.r1<=.07 and b.volume>=1.5*b.v20 and b.close>=.99*b.high20 and b.r20<.25 and b.amount20>=5e7):continue
        if not (p.volume<=.85*b.volume and p.low>=.98*b.low and p.close>=.97*b.close):continue
        if not (t.close>b.high and t.volume>=1.15*t.v20 and -.02<=t.r1<=.07):continue
        buy=g.iloc[i+1]
        if buy.open>t.close*1.07:continue
        lim=.195 if code.startswith(("300","301")) else .095
        if buy.open>=t.close*(1+lim):continue
        price=float(buy.open)
        if not price>0:continue
        h3=g.iloc[i+1:i+4].high.max()
        low3=g.iloc[i+1:i+4].low.min()
        items.append(dict(symbol=code,signal_date=t.date.strftime("%Y-%m-%d"),entry_date=buy.date.strftime("%Y-%m-%d"),
            entry_open=price,net_5d=float(g.iloc[i+6].close/price-1-.0018),net_10d=float(g.iloc[i+11].close/price-1-.0018),
            hit_3d_high_ge3pct=int(h3>=price*1.03),low_3d_drawdown=float(low3/price-1),
            volume_ratio=float(t.volume/t.v20),relative_strength_5d=float(t.close/g.iloc[i-5].close-1)))
    return items
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--scope",choices=("full","pilot"),default="full")
    a.add_argument("--shards",type=int,default=8)
    a.add_argument("--shard-index",type=int,default=0)
    a.add_argument("--output",default="results")
    args=a.parse_args()
    import akshare as ak
    out=Path(args.output);out.mkdir(exist_ok=True,parents=True)
    codes,delisted=universe(ak)
    if args.scope=="pilot":
        sample={"000625","000725","002100","002714","300394","603606","600886","600339","002281","600028","300142","603083","000988","600276","300308","300502"}
        codes=[c for c in codes if c in sample]
    codes=[c for i,c in enumerate(codes) if i%args.shards==args.shard_index]
    good=0;errs={};rows=[]
    print("START",len(codes),"shard",args.shard_index,flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks=[pool.submit(fetch,c) for c in codes]
        for j,fu in enumerate(as_completed(tasks),1):
            c,f,err=fu.result()
            if err:errs[c]=err
            else:
                good+=1;rows.extend(signals(c,f))
            if j%100==0:print("PROGRESS",j,len(codes),good,len(rows),flush=True)
    pd.DataFrame(rows,columns=FIELDS).to_csv(out/"signals.csv",index=False)
    quality=dict(scope=args.scope,attempted=len(codes),downloaded=good,delisted_codes_recovered=delisted,
                 events=len(rows),errors=len(errs),window=START+".."+END)
    (out/"coverage.json").write_text(json.dumps(quality,indent=2))
    (out/"errors.json").write_text(json.dumps(errs,ensure_ascii=False,indent=2))
    print(json.dumps(quality),flush=True)
    if good < len(codes)*.75 or not rows:raise SystemExit("NO RELIABLE FULL BACKTEST: incomplete data")
if __name__=="__main__":main()

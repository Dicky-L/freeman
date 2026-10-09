import json,sys
from pathlib import Path
import pandas as pd
root=Path(sys.argv[1] if len(sys.argv)>1 else "collected")
cfiles=list(root.rglob("coverage.json"))
sfiles=list(root.rglob("signals.csv"))
if not cfiles or not sfiles:raise SystemExit("NO REPORT: no source artifacts")
coverage=[json.loads(p.read_text()) for p in cfiles]
total=sum(x["attempted"] for x in coverage);good=sum(x["downloaded"] for x in coverage)
frames=[pd.read_csv(p,dtype={"symbol":str}) for p in sfiles]
raw=pd.concat(frames,ignore_index=True).dropna(subset=["signal_date"])
if raw.empty:raise SystemExit("NO REPORT: no qualifying events")
raw=raw.sort_values(["signal_date","relative_strength_5d","volume_ratio"],ascending=[True,False,False])
top=raw.groupby("signal_date").head(10)
top.to_csv("top10_signals.csv",index=False)
r={"symbol_coverage":round(good/max(1,total),4),"stocks_scanned":good,"stocks_attempted":total,"raw_events":len(raw),"top10_events":len(top),
"top10_net5_win_rate":round(float((top.net_5d>0).mean()),4),"top10_net5_mean":round(float(top.net_5d.mean()),5),
"top10_net10_mean":round(float(top.net_10d.mean()),5),"top10_3d_high_hit":round(float(top.hit_3d_high_ge3pct.mean()),4),
"data_quality_approved":False,"limitations":["Unadjusted corporate-action prices","Historical ST/delist coverage incomplete","Not a portfolio simulation","No price limits/suspension perfect fill","No rolling out-of-sample validation","Cost fixed at 0.18% rather than historical broker rates"]}
Path("report.json").write_text(json.dumps(r,ensure_ascii=False,indent=2))
Path("REPORT.md").write_text("# 近5年A股形态回测初步结果\n\n**非可交易策略绩效，数据质量尚未通过完整验证。**\n\n"+json.dumps(r,ensure_ascii=False,indent=2))
print(json.dumps(r,ensure_ascii=False,indent=2))

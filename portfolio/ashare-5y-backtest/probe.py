"""Check BaoStock connectivity and minimum viable data before an expensive full scan."""
import json
import baostock as bs
lg=bs.login()
assert lg.error_code=="0",f"BaoStock login failed: {lg.error_code} {lg.error_msg}"
try:
  q=bs.query_stock_basic()
  assert q.error_code=="0",f"stock basics: {q.error_msg}"
  basic=q.get_data()
  assert len(basic)>=3000,f"unexpected universe size {len(basic)}"
  assert {"code","ipoDate","outDate","status","type"}.issubset(basic.columns)
  rs=bs.query_history_k_data_plus("sh.603606","date,open,high,low,close,volume,amount,tradestatus,isST",
      start_date="2026-09-01",end_date="2026-09-30",frequency="d",adjustflag="3")
  assert rs.error_code=="0",f"K-line query: {rs.error_msg}"
  rows=rs.get_data()
  assert len(rows)>=10,f"missing K-line rows: {len(rows)}"
  print(json.dumps({"result":"PASS","provider":"baostock","basic_count":len(basic),
      "603606_rows":len(rows)},ensure_ascii=False),flush=True)
finally:
  bs.logout()

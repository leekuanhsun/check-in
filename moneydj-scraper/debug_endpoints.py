"""一次性除錯腳本：印出 MI_MARGN / BWIBBU_ALL / T86 的真實欄位名稱與範例列，
用來核對 twse_api.py 裡的欄位索引是否正確。跑完就可以刪除。
"""
import json
from datetime import date, timedelta

import requests

MARGIN_URL = "https://www.twse.com.tw/exchangeReport/MI_MARGN"
VALUATION_URL = "https://www.twse.com.tw/exchangeReport/BWIBBU_ALL"
INSTITUTIONAL_URL = "https://www.twse.com.tw/fund/T86"


def recent_weekday(offset=0):
    d = date.today() - timedelta(days=offset)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


d = recent_weekday(1)
date_str = d.strftime("%Y%m%d")
print("=== MI_MARGN ===", date_str)
resp = requests.get(MARGIN_URL, params={"response": "json", "date": date_str, "selectType": "ALL"}, timeout=15)
payload = resp.json()
print("top-level keys:", list(payload.keys()))
print("fields:", payload.get("fields"))
data = payload.get("data") or (payload.get("tables", [{}])[0].get("data") if payload.get("tables") else None)
print("first row:", data[0] if data else None)
print("row len:", len(data[0]) if data else None)
if "tables" in payload:
    for t in payload["tables"]:
        print("table title:", t.get("title"), "fields:", t.get("fields"))
        if t.get("data"):
            print("  first row:", t["data"][0], "len:", len(t["data"][0]))

print()
print("=== BWIBBU_ALL ===")
resp2 = requests.get(VALUATION_URL, params={"response": "json"}, timeout=15)
payload2 = resp2.json()
print("top-level keys:", list(payload2.keys()))
print("fields:", payload2.get("fields"))
data2 = payload2.get("data")
print("first row:", data2[0] if data2 else None)

print()
print("=== T86 ===", date_str)
resp3 = requests.get(INSTITUTIONAL_URL, params={"response": "json", "date": date_str, "selectType": "ALL"}, timeout=15)
payload3 = resp3.json()
print("top-level keys:", list(payload3.keys()))
print("fields:", payload3.get("fields"))
data3 = payload3.get("data")
# find TSMC row (2330) to sanity check magnitude
row_2330 = next((r for r in (data3 or []) if str(r[0]).strip() == "2330"), None)
print("2330 row:", row_2330)
print("row len:", len(row_2330) if row_2330 else None)

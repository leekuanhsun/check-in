"""一次性除錯腳本：印出全市場端點（t187ap03_L / STOCK_DAY_ALL）的真實回應結構，
用來核對 twse_api.py 裡 parse_all_companies / parse_all_stock_day 的解析邏輯是否正確。
跑完就可以刪除。
"""
import json

import requests

from twse_api import ALL_COMPANIES_URL, ALL_STOCK_DAY_URL

print("=== t187ap03_L (all companies) ===")
resp = requests.get(ALL_COMPANIES_URL, timeout=30)
print("status:", resp.status_code)
payload = resp.json()
print("top-level type:", type(payload).__name__)
if isinstance(payload, list):
    print("count:", len(payload))
    print("first row:", json.dumps(payload[0], ensure_ascii=False))
    # 找台積電核對
    tsmc = next((r for r in payload if str(r.get("公司代號", "")).strip() == "2330"), None)
    print("2330 row:", json.dumps(tsmc, ensure_ascii=False))
elif isinstance(payload, dict):
    print("keys:", list(payload.keys()))
    print(json.dumps(payload, ensure_ascii=False)[:1500])

print()
print("=== STOCK_DAY_ALL (all stocks today) ===")
resp2 = requests.get(ALL_STOCK_DAY_URL, params={"response": "json"}, timeout=30)
print("status:", resp2.status_code)
payload2 = resp2.json()
print("top-level keys:", list(payload2.keys()) if isinstance(payload2, dict) else type(payload2).__name__)
if isinstance(payload2, dict):
    print("fields:", payload2.get("fields"))
    data = payload2.get("data", [])
    print("row count:", len(data))
    print("first row:", data[0] if data else None)
    tsmc_row = next((r for r in data if str(r[0]).strip() == "2330"), None)
    print("2330 row:", tsmc_row)
    print("2330 row len:", len(tsmc_row) if tsmc_row else None)

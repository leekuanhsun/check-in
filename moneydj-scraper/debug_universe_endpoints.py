"""一次性除錯腳本：印出全市場端點的真實回應結構，用來核對/建立
parse_all_companies / parse_all_stock_day 需要的解析邏輯與產業別代碼對照表。跑完就可以刪除。
"""
import json
from collections import defaultdict

import requests

from twse_api import ALL_COMPANIES_URL

print("=== t187ap03_L (all companies) ===")
resp = requests.get(ALL_COMPANIES_URL, timeout=30)
print("status:", resp.status_code)
payload = resp.json()
print("count:", len(payload))

# 產業別是代碼（如 "24"），不是文字，這裡把每個代碼底下的公司簡稱列出來，
# 方便用「這個代碼底下都是哪些公司」反推代碼對應的產業名稱。
by_code = defaultdict(list)
for row in payload:
    code = str(row.get("產業別", "")).strip()
    name = str(row.get("公司簡稱", "")).strip()
    by_code[code].append(name)

print(f"distinct industry codes: {len(by_code)}")
for code in sorted(by_code.keys()):
    names = by_code[code]
    sample = "、".join(names[:6])
    print(f"  code={code!r:6} count={len(names):4}  sample: {sample}")

print()
print("=== candidate all-stock-quote endpoints ===")
candidates = [
    ("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", {}),
    ("https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL", {"response": "json"}),
    ("https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL", {"response": "json"}),
    ("https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX", {}),
]
for url, params in candidates:
    print(f"--- {url} params={params} ---")
    try:
        r = requests.get(url, params=params, timeout=30)
        print("status:", r.status_code, "content-type:", r.headers.get("content-type"))
        text = r.text
        print("raw text head:", text[:300].replace("\n", " "))
        try:
            data = r.json()
            if isinstance(data, list):
                print("parsed OK: list, len=", len(data))
                if data:
                    print("first item:", json.dumps(data[0], ensure_ascii=False)[:500])
            elif isinstance(data, dict):
                print("parsed OK: dict, keys=", list(data.keys()))
                if "fields" in data:
                    print("fields:", data.get("fields"))
                if "data" in data and data["data"]:
                    print("first row:", data["data"][0])
        except Exception as e:
            print("json parse failed:", e)
    except Exception as e:
        print("request failed:", e)
    print()

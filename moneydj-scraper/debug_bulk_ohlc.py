"""TEMP debug script: verify whether MI_INDEX (type=ALLBUT0999) gives bulk
per-stock OHLC for an arbitrary historical date, which would make full-universe
K-line backfill feasible (O(days) instead of O(stocks x months)). Not permanent.
"""
import json
import urllib.request
from datetime import date, timedelta


def fetch(url, params):
    from urllib.parse import urlencode
    full_url = url + "?" + urlencode(params)
    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.headers.get("Content-Type")


# pick a recent past weekday, avoiding "today might not have closed yet"
d = date.today() - timedelta(days=5)
while d.weekday() >= 5:
    d -= timedelta(days=1)
date_str = d.strftime("%Y%m%d")
print(f"testing date: {date_str}")

url = "https://www.twse.com.tw/exchangeReport/MI_INDEX"
raw, ctype = fetch(url, {"response": "json", "date": date_str, "type": "ALLBUT0999"})
print("content-type:", ctype, "len:", len(raw))
try:
    data = json.loads(raw)
    print("top-level keys:", list(data.keys()))
    if "tables" in data:
        for i, t in enumerate(data["tables"]):
            fields = t.get("fields") or []
            print(f"table[{i}]: title={t.get('title')!r} fields={fields} rows={len(t.get('data') or [])}")
            if t.get("data"):
                print(f"  sample row: {t['data'][0]}")
    if "fields" in data:
        print("fields:", data["fields"])
        print("sample data row:", (data.get("data") or [None])[0])
except Exception as e:
    print("JSON parse failed:", e)
    print("raw text sample:", raw[:500])

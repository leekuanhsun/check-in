"""TEMP debug script: find real TWSE endpoint(s) that classify instrument type
(ETF / warrant / beneficiary certificate / etc.) for stock_ids not covered by
t187ap03_L (common-stock company list). Not part of the permanent codebase.
"""
import json
import urllib.request

TARGET_IDS = {"0050", "00400A", "01001T", "020000", "02001L", "020036"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


print("=== fetching swagger catalog ===")
try:
    raw = fetch("https://openapi.twse.com.tw/v1/swagger.json")
    data = json.loads(raw)
    paths = list(data.get("paths", {}).keys())
    print(f"total paths: {len(paths)}")
    for p in paths:
        pl = p.lower()
        if "etf" in pl or "isin" in pl or "opendata" in p:
            print(p)
except Exception as e:
    print("swagger fetch failed:", e)

print()
print("=== candidate opendata endpoints ===")
candidates = [
    "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",  # known-good: common stock
    "https://openapi.twse.com.tw/v1/opendata/t187ap46_L_1",  # guess: ETF list?
    "https://openapi.twse.com.tw/v1/opendata/t187ap41_L",  # guess: warrant list?
]
for url in candidates:
    try:
        raw = fetch(url)
        data = json.loads(raw)
        if isinstance(data, list):
            print(url, "-> list len", len(data), "sample keys:", list(data[0].keys()) if data else None)
        else:
            print(url, "-> non-list:", str(data)[:200])
    except Exception as e:
        print(url, "-> FAILED:", e)

print()
print("=== ISIN public HTML lookup (strMode by instrument type) ===")
for mode in [2, 4, 5, 7]:
    url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
    try:
        raw = fetch(url)
        text = raw.decode("big5", errors="replace")
        # print first table row after header to see shape
        snippet = text[text.find("<tbody"):text.find("<tbody") + 800] if "<tbody" in text else text[:500]
        print(f"--- strMode={mode} (len={len(text)}) ---")
        print(snippet[:600])
    except Exception as e:
        print(url, "-> FAILED:", e)

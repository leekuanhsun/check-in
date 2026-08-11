"""TEMP: print stats about a freshly-generated universe_detail.json (dry run)."""
import json

d = json.load(open("universe_detail.json", encoding="utf-8"))
print("total stocks:", len(d))
r = d.get("2330", {})
print("2330 ohlc rows:", len(r.get("ohlc", [])))
print("2330 institutional rows:", len(r.get("institutional", [])))
print("2330 margin rows:", len(r.get("margin", [])))
print("2330 fundamentals:", r.get("fundamentals"))
print("2330 insights:", r.get("insights"))
got_ohlc = sum(1 for v in d.values() if v.get("ohlc"))
print("stocks with any ohlc:", got_ohlc, "/", len(d))

"""產生範例個股明細（K線/三大法人買賣超/融資融券/基本資訊），供儀表板展示用。

跟 generate_sample_data.py 一樣，因為這個環境連不到 TWSE，暫時無法用 twse_api.py
對真實端點跑資料，所以用本腳本產生格式與 fetch_stock_details() 輸出完全一致的範例資料
（虛構數字，收盤價序列的最後一天會對齊 sample_output.json 對應股票的 close_price，
方便儀表板展示時價格連續）。待日後在可連外環境用 main.py --with-detail 取得真實資料後，
可直接取代本檔案輸出的 sample_detail.json。
"""
import json
import random
from datetime import date, timedelta

from insights import summarize_stock_insights

random.seed(20260810)

with open("sample_output.json", "r", encoding="utf-8") as f:
    records = json.load(f)


def _trading_days(n, end=date(2026, 8, 9)):
    days = []
    cursor = end
    while len(days) < n:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


def _gen_ohlc(target_close, n=40):
    days = _trading_days(n)
    # 從隨機起點走 random walk，最後一天硬對齊 target_close，讓範例資料跟 sample_output.json 一致
    price = target_close * random.uniform(0.85, 1.15)
    rows = []
    for i, d in enumerate(days):
        drift = random.uniform(-0.02, 0.02)
        price = max(1.0, price * (1 + drift))
        if i == len(days) - 1:
            price = target_close
        open_p = price * random.uniform(0.99, 1.01)
        high = max(open_p, price) * random.uniform(1.0, 1.02)
        low = min(open_p, price) * random.uniform(0.98, 1.0)
        volume = random.randint(800, 45000) * 1000
        rows.append(
            {
                "date": d.isoformat(),
                "open": round(open_p, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(price, 2),
                "volume": volume,
            }
        )
    return rows


def _gen_institutional(n=10):
    days = _trading_days(n)
    return [
        {
            "date": d.isoformat(),
            "foreign": random.randint(-3000, 3000),
            "trust": random.randint(-800, 800),
            "dealer": random.randint(-500, 500),
        }
        for d in days
    ]


def _gen_margin(n=10):
    days = _trading_days(n)
    margin_balance = random.randint(5000, 60000)
    short_balance = random.randint(500, 8000)
    rows = []
    for d in days:
        margin_change = random.randint(-1500, 1500)
        short_change = random.randint(-300, 300)
        margin_balance = max(0, margin_balance + margin_change)
        short_balance = max(0, short_balance + short_change)
        rows.append(
            {
                "date": d.isoformat(),
                "margin_balance": margin_balance,
                "margin_change": margin_change,
                "short_balance": short_balance,
                "short_change": short_change,
            }
        )
    return rows


def _gen_fundamentals():
    return {
        "pe_ratio": round(random.uniform(8, 32), 2),
        "dividend_yield": round(random.uniform(0.8, 6.5), 2),
        "pb_ratio": round(random.uniform(1.2, 9.0), 2),
    }


detail = {}
for r in records:
    stock_id = r["stock_id"]
    target_close = float(r["close_price"])
    ohlc = _gen_ohlc(target_close)
    institutional = _gen_institutional()
    margin = _gen_margin()
    detail[stock_id] = {
        "ohlc": ohlc,
        "institutional": institutional,
        "margin": margin,
        "fundamentals": _gen_fundamentals(),
        "insights": summarize_stock_insights(ohlc, institutional, margin),
    }

with open("sample_detail.json", "w", encoding="utf-8") as f:
    json.dump(detail, f, ensure_ascii=False, indent=2)

print(f"wrote detail for {len(detail)} stocks to sample_detail.json")

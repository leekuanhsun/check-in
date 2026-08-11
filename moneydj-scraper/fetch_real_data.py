"""用 TWSE 官方端點抓真實資料，取代範例資料。

分類／角色（概念股歸類）沿用既有的人工整理清單（供應鏈上下游關係屬公開常識性
分類，非爬自特定頁面）；股價／K線／三大法人買賣超／融資融券／基本資訊則全部
來自 twse_api.py 對接的 TWSE 官方公開端點，是真實資料。

本腳本需要能連上 www.twse.com.tw，設計給有網路的環境（例如 GitHub Actions）執行；
在網路政策受限的沙盒中執行會因連線失敗而拿到空結果，不會拋例外中斷。
"""
import json
from dataclasses import asdict

from concept_categories import CATEGORIES
from insights import summarize_stock_insights
from models import StockRecord
from twse_api import fetch_stock_details


def main() -> None:
    stock_ids = [sid for stocks in CATEGORIES.values() for sid, _, _ in stocks]
    name_role_category = {
        sid: (name, role, category)
        for category, stocks in CATEGORIES.items()
        for sid, name, role in stocks
    }

    print(f"fetching TWSE detail for {len(stock_ids)} stocks...")
    details = fetch_stock_details(stock_ids)

    records = []
    detail_out = {}
    for sid in stock_ids:
        name, role, category = name_role_category[sid]
        detail = details.get(sid, {"ohlc": [], "institutional": [], "margin": [], "fundamentals": {}})
        ohlc = detail.get("ohlc", [])

        close_price = change = change_pct = volume = None
        if ohlc:
            latest = ohlc[-1]
            close_price = latest.get("close")
            volume = latest.get("volume")
            if len(ohlc) >= 2 and ohlc[-2].get("close"):
                prev_close = ohlc[-2]["close"]
                if close_price is not None and prev_close:
                    change = close_price - prev_close
                    change_pct = change / prev_close * 100

        records.append(
            StockRecord(
                stock_id=sid,
                stock_name=name,
                role=role,
                close_price=f"{close_price:.2f}" if close_price is not None else None,
                change=f"{change:+.2f}" if change is not None else None,
                change_pct=f"{change_pct:+.2f}%" if change_pct is not None else None,
                volume=f"{volume:,}" if volume is not None else None,
                category=category,
                source_url="https://www.twse.com.tw/exchangeReport/STOCK_DAY",
            )
        )

        detail["insights"] = summarize_stock_insights(
            detail.get("ohlc", []), detail.get("institutional", []), detail.get("margin", [])
        )
        detail_out[sid] = detail

    with open("real_concept_stocks.json", "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)

    with open("real_concept_detail.json", "w", encoding="utf-8") as f:
        json.dump(detail_out, f, ensure_ascii=False, indent=2)

    got_price = sum(1 for r in records if r.close_price)
    print(
        f"wrote real_concept_stocks.json ({got_price}/{len(records)} with price) "
        "and real_concept_detail.json"
    )


if __name__ == "__main__":
    main()

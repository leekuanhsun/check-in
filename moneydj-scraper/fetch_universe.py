"""抓取全部上市（TWSE）股票的代碼／名稱／官方產業分類／當日價格，涵蓋整個上市股票母體。

跟 fetch_real_data.py 不同：那支是針對少量精選概念股，逐檔抓完整的 K 線／三大法人／
融資融券歷史明細；這支是用兩個「全市場一次撈完」的端點（fetch_all_companies /
fetch_all_stock_day），只抓「當下快照」（代碼/名稱/官方產業別/收盤/漲跌/成交量），
涵蓋全部上市股票（約 1000+ 檔）。不會對 1000+ 檔股票逐一抓歷史 K 線／法人／資券——
那樣會是數萬次請求，時間跟對 TWSE 伺服器的負擔都不合理。想看特定股票的 K 線/法人/
資券明細，用 fetch_real_data.py 把該股票加進 concept_categories.py 後單獨抓。

category 欄位是 TWSE 官方產業別分類（半導體業、電子零組件業……），不是人工整理的
概念股主題；concept_theme 欄位則保留 concept_categories.py 裡的概念股主題名稱
（例如「AI 伺服器供應鏈」），只有在該清單裡的股票才會有值，其餘股票是 None。

上櫃（TPEX）股票不在這份清單裡——TWSE 全市場端點本來就只涵蓋上市股票，等效的上櫃
端點在 www.tpex.org.tw，尚未串接。
"""
import json
from dataclasses import asdict

from concept_categories import CATEGORIES
from models import StockRecord
from twse_api import fetch_all_companies, fetch_all_stock_day


def _concept_lookup():
    """從 concept_categories.py 建立 {stock_id: (concept_theme, role)} 對照表。"""
    lookup = {}
    for theme, stocks in CATEGORIES.items():
        for stock_id, _name, role in stocks:
            lookup[stock_id] = (theme, role)
    return lookup


def main() -> None:
    print("fetching full TWSE-listed company list...")
    companies = fetch_all_companies()
    print(f"got {len(companies)} companies")

    print("fetching today's all-market quotes...")
    quotes = fetch_all_stock_day()
    print(f"got {len(quotes)} quotes")

    concept_lookup = _concept_lookup()

    # 以「公司清單」為主體：確保每家上市公司都出現一筆，即使當天沒有成交量資料。
    stock_ids = sorted(set(companies) | set(quotes))

    records = []
    for stock_id in stock_ids:
        company = companies.get(stock_id, {})
        quote = quotes.get(stock_id, {})
        theme, concept_role = concept_lookup.get(stock_id, (None, None))

        close = quote.get("close")
        change = quote.get("change")
        change_pct = None
        if close is not None and change is not None:
            prev_close = close - change
            if prev_close:
                change_pct = change / prev_close * 100

        records.append(
            StockRecord(
                stock_id=stock_id,
                stock_name=company.get("name") or quote.get("name"),
                role=concept_role,
                close_price=f"{close:.2f}" if close is not None else None,
                change=f"{change:+.2f}" if change is not None else None,
                change_pct=f"{change_pct:+.2f}%" if change_pct is not None else None,
                volume=f"{quote['volume']:,}" if quote.get("volume") is not None else None,
                category=company.get("industry") or "未分類",
                concept_theme=theme,
                source_url="https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
            )
        )

    with open("universe_stocks.json", "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)

    got_price = sum(1 for r in records if r.close_price)
    got_industry = sum(1 for r in records if r.category and r.category != "未分類")
    print(
        f"wrote universe_stocks.json: {len(records)} companies, "
        f"{got_price} with price, {got_industry} with industry classification"
    )


if __name__ == "__main__":
    main()

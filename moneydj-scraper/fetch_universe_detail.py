"""抓取「全市場」股票的 K 線／三大法人買賣超／融資融券／基本資訊，涵蓋
fetch_universe.py 清單裡的所有股票（不限 concept_categories.py 那 24 檔精選概念股）。

跟 fetch_real_data.py 不同：那支對每一檔股票各打一次 STOCK_DAY（逐檔逐月），股票數一多
（~1000+ 檔）請求數會是數萬次，不可行；這支全部改用「全市場一次撈完」的端點
（twse_api.fetch_universe_details，內部用 MI_INDEX／T86／MI_MARGN／BWIBBU_ALL），
每個交易日只呼叫一次，總請求數只跟天數成正比、不跟股票數成正比。

跟 fetch_universe.py 不同：那支只抓「當下快照」（代碼/名稱/官方產業分類/當日價格）；
這支抓「歷史明細」（K 線/法人/資券/基本資訊），寫到 universe_detail.json，讓
dashboard 裡任何一檔股票都能看到完整明細，不只 24 檔精選概念股。
"""
import json

from insights import summarize_stock_insights
from twse_api import fetch_all_companies, fetch_all_stock_day, fetch_universe_details


def main() -> None:
    print("fetching stock universe (companies + quotes)...")
    companies = fetch_all_companies()
    quotes = fetch_all_stock_day()
    stock_ids = sorted(set(companies) | set(quotes))
    print(f"backfilling detail for {len(stock_ids)} stocks...")

    details = fetch_universe_details(stock_ids)

    for detail in details.values():
        detail["insights"] = summarize_stock_insights(
            detail.get("ohlc", []), detail.get("institutional", []), detail.get("margin", [])
        )

    with open("universe_detail.json", "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    got_ohlc = sum(1 for d in details.values() if d.get("ohlc"))
    print(
        f"wrote universe_detail.json: {len(details)} stocks, "
        f"{got_ohlc} with OHLC data"
    )


if __name__ == "__main__":
    main()

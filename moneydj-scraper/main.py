"""CLI 入口：讀取 targets 清單 → 呼叫 run_batch → 輸出結果。"""
import argparse
import json
from typing import Dict, List

from aggregate import summarize_by_stock
from company_map import load_company_map, resolve_company_targets
from parser import rank_today_gainers
from scraper import MoneyDJConceptScraper


def _load_targets(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_targets(args, parser: argparse.ArgumentParser) -> List[Dict[str, str]]:
    if args.company:
        if not args.company_map:
            parser.error("--company 需要搭配 --company-map 指定對照表 JSON")
        company_map = load_company_map(args.company_map)
        targets = resolve_company_targets(company_map, args.company)
        if targets is None:
            parser.error(f"在 {args.company_map} 找不到公司「{args.company}」（含別名）")
        return targets

    if args.targets:
        return _load_targets(args.targets)

    parser.error("需要指定 --targets，或 --company + --company-map，或 --inspect 其中一種")


def main() -> None:
    parser = argparse.ArgumentParser(description="供應鏈概念股爬蟲（不限定單一資料來源）")
    parser.add_argument("--targets", help="JSON 檔，內容為 [{'url':..., 'category':...}, ...]")
    parser.add_argument(
        "--company", help="用美股公司名稱/別名查對照表（需搭配 --company-map），取代 --targets"
    )
    parser.add_argument(
        "--company-map",
        help="美股公司 → 台灣供應鏈概念股頁面對照表 JSON（見 company_map.example.json）",
    )
    parser.add_argument("--output", default="moneydj_concept_stocks.json", help="輸出 JSON 路徑")
    parser.add_argument(
        "--summary-output",
        help="若指定路徑，額外輸出跨來源彙整結果（同一檔股票在幾個網站都被列為概念股）",
    )
    parser.add_argument("--inspect", help="只印出指定 URL 的表格結構，不執行完整爬取")
    parser.add_argument("--top", type=int, default=10, help="顯示當日漲幅排行前 N 名")
    parser.add_argument(
        "--quotes-source",
        choices=["moneydj", "tradingview"],
        default="moneydj",
        help="價格資料來源：moneydj（預設，直接用頁面上的欄位）或 "
        "tradingview（分類/成分股仍照原頁面抓，報價改用 TradingView 覆蓋，"
        "屬未公開端點，使用前請先看 README 的注意事項）",
    )
    args = parser.parse_args()

    scraper = MoneyDJConceptScraper()

    if args.inspect:
        scraper.inspect_page(args.inspect)
        return

    targets = _resolve_targets(args, parser)

    if args.quotes_source == "tradingview":
        records = scraper.run_batch_with_tradingview_quotes(targets)
    else:
        records = scraper.run_batch(targets)
    scraper.save_json(records, args.output)

    if args.summary_output:
        summary = summarize_by_stock(records)
        with open(args.summary_output, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        multi_source = [s for s in summary if s["source_count"] > 1]
        print(f"跨來源彙整已寫入 {args.summary_output}（{len(multi_source)} 檔出現在一個以上來源）")

    top_gainers = rank_today_gainers(records, top_n=args.top)
    print(f"當日漲幅排行前 {len(top_gainers)} 名（僅供參考，非預測）：")
    for r in top_gainers:
        print(f"  {r.stock_id} {r.stock_name}: {r.change_pct}")


if __name__ == "__main__":
    main()

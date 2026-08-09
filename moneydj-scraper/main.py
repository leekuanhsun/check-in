"""CLI 入口：讀取 targets 清單 → 呼叫 run_batch → 輸出結果。"""
import argparse
import json
from typing import Dict, List

from parser import rank_today_gainers
from scraper import MoneyDJConceptScraper


def _load_targets(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="MoneyDJ 概念股爬蟲")
    parser.add_argument("--targets", help="JSON 檔，內容為 [{'url':..., 'category':...}, ...]")
    parser.add_argument("--output", default="moneydj_concept_stocks.json", help="輸出 JSON 路徑")
    parser.add_argument("--inspect", help="只印出指定 URL 的表格結構，不執行完整爬取")
    parser.add_argument("--top", type=int, default=10, help="顯示當日漲幅排行前 N 名")
    args = parser.parse_args()

    scraper = MoneyDJConceptScraper()

    if args.inspect:
        scraper.inspect_page(args.inspect)
        return

    if not args.targets:
        parser.error("--targets 或 --inspect 至少需要指定一個")

    targets = _load_targets(args.targets)
    records = scraper.run_batch(targets)
    scraper.save_json(records, args.output)

    top_gainers = rank_today_gainers(records, top_n=args.top)
    print(f"當日漲幅排行前 {len(top_gainers)} 名（僅供參考，非預測）：")
    for r in top_gainers:
        print(f"  {r.stock_id} {r.stock_name}: {r.change_pct}")


if __name__ == "__main__":
    main()

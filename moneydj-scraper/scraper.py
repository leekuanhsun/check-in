"""批次控制層 + 輸出層 + 除錯工具。"""
import json
import logging
import random
import time
from dataclasses import asdict
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from fetcher import fetch_html
from logging_config import setup_logging
from models import StockRecord
from parser import parse_page
from tradingview import apply_quote, fetch_quotes, resolve_symbols

setup_logging()
logger = logging.getLogger(__name__)


class MoneyDJConceptScraper:
    def __init__(
        self,
        timeout: int = 10,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        retries: int = 3,
    ):
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.retries = retries

    def scrape_one(self, url: str, category: Optional[str] = None) -> List[StockRecord]:
        html = fetch_html(url, timeout=self.timeout, retries=self.retries)
        if html is None:
            return []
        records = parse_page(html, category=category, source_url=url)
        logger.info("scraped %d records from %s", len(records), url)
        return records

    def run_batch(self, targets: List[Dict[str, str]]) -> List[StockRecord]:
        all_records: List[StockRecord] = []
        for i, target in enumerate(targets):
            url = target["url"]
            category = target.get("category")
            all_records.extend(self.scrape_one(url, category=category))
            if i < len(targets) - 1:
                time.sleep(random.uniform(self.min_delay, self.max_delay))
        return all_records

    def run_batch_with_tradingview_quotes(self, targets: List[Dict[str, str]]) -> List[StockRecord]:
        """先用 MoneyDJ 取得分類/成分股，再用 TradingView 覆蓋報價欄位。

        解析不到 TradingView symbol 或查無報價的股票，保留 MoneyDJ 原本解析出的
        價格欄位（若有）作為備援，不會整筆捨棄。
        """
        records = self.run_batch(targets)

        stock_ids = sorted({r.stock_id for r in records if r.stock_id})
        symbol_map = resolve_symbols(stock_ids)
        quotes = fetch_quotes(list(symbol_map.values()))
        logger.info(
            "resolved %d/%d symbols, got quotes for %d",
            len(symbol_map), len(stock_ids), len(quotes),
        )

        for record in records:
            symbol = symbol_map.get(record.stock_id)
            quote = quotes.get(symbol) if symbol else None
            updated = apply_quote(asdict(record), quote)
            for key, value in updated.items():
                setattr(record, key, value)
        return records

    def save_json(self, records: List[StockRecord], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)
        logger.info("saved %d records to %s", len(records), path)

    def inspect_page(self, url: str, top_n: int = 5) -> None:
        html = fetch_html(url, timeout=self.timeout, retries=self.retries)
        if html is None:
            logger.error("could not fetch %s for inspection", url)
            return
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        logger.info("found %d tables on %s", len(tables), url)
        for i, table in enumerate(tables[:top_n]):
            print(f"--- table[{i}] ({len(table.find_all('tr'))} rows) ---")
            print(table.prettify()[:3000])

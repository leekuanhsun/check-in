"""MoneyDJ 概念股/供應鏈頁面爬蟲。

擷取股票代碼、名稱、當日價格與漲跌幅，輸出結構化 JSON。
僅做資料擷取與「當日漲跌幅排序」，不含任何股價預測邏輯。
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

LOG_PATH = Path(__file__).with_name("moneydj_scraper.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("moneydj_scraper")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",
]

# MoneyDJ 頁面以 Big5 編碼為主，依序嘗試解碼
ENCODING_CANDIDATES = ["big5", "cp950", "utf-8"]

ID_NAME_PATTERNS = [
    re.compile(r"^(?P<id>\d{4,6})\s*(?P<name>\S+)$"),  # "2330 台積電"
    re.compile(r"^(?P<name>\S+?)\s*[\(（](?P<id>\d{4,6})[\)）]$"),  # "台積電(2330)"
]

HREF_ID_KEYS = ["code", "id", "stockid", "s", "a"]


@dataclass
class StockRecord:
    stock_id: Optional[str]
    stock_name: Optional[str]
    role: Optional[str] = None
    close_price: Optional[str] = None
    change: Optional[str] = None
    change_pct: Optional[str] = None
    volume: Optional[str] = None
    category: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def change_pct_float(self) -> Optional[float]:
        if not self.change_pct:
            return None
        try:
            return float(self.change_pct.replace("%", "").replace(",", "").strip())
        except ValueError:
            return None


def _split_id_and_name(text: str) -> tuple[Optional[str], Optional[str]]:
    """從 "2330 台積電" 或 "台積電(2330)" 這類文字擷取 (代碼, 名稱)。"""
    text = text.strip()
    for pattern in ID_NAME_PATTERNS:
        match = pattern.match(text)
        if match:
            return match.group("id"), match.group("name")
    return None, text or None


def _extract_id_from_href(href: str) -> Optional[str]:
    """從連結 query string 中取得股票代碼（文字擷取失敗時的備援）。"""
    if not href:
        return None
    query = parse_qs(urlparse(href).query)
    for key in HREF_ID_KEYS:
        values = query.get(key)
        if values and re.fullmatch(r"\d{4,6}", values[0]):
            return values[0]
    match = re.search(r"\b(\d{4,6})\b", href)
    return match.group(1) if match else None


class MoneyDJConceptScraper:
    def __init__(self, timeout: int = 10, min_delay: float = 2.0, max_delay: float = 5.0):
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay

    def _fetch_html(self, url: str, timeout: Optional[int] = None) -> Optional[str]:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://www.moneydj.com/",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=timeout or self.timeout)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.error("fetch failed for %s: %s", url, exc)
            return None

        for encoding in ENCODING_CANDIDATES:
            try:
                return resp.content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return resp.content.decode("utf-8", errors="replace")

    def parse_page(
        self, html: str, category: Optional[str] = None, source_url: Optional[str] = None
    ) -> List[StockRecord]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            logger.warning("no <table> found on page (%s)", source_url)
            return []

        target_table = max(tables, key=lambda t: len(t.find_all("tr")))
        records: List[StockRecord] = []
        for row in target_table.find_all("tr"):
            cells = row.find_all(["td"])
            if not cells:
                continue
            record = self._parse_row(cells, category=category, source_url=source_url)
            if record is not None:
                records.append(record)
        return records

    def _parse_row(
        self, cells, category: Optional[str] = None, source_url: Optional[str] = None
    ) -> Optional[StockRecord]:
        try:
            texts = [c.get_text(strip=True) for c in cells]
            if len(texts) < 2 or not texts[0]:
                return None

            stock_id, stock_name = _split_id_and_name(texts[0])
            if stock_id is None:
                link = cells[0].find("a", href=True)
                if link is not None:
                    stock_id = _extract_id_from_href(link["href"])
            if stock_id is None:
                return None

            pct_index = next((i for i, t in enumerate(texts) if "%" in t), None)

            def _pick(index: Optional[int]) -> Optional[str]:
                if index is None or index < 0 or index >= len(texts):
                    return None
                return texts[index] or None

            change_pct = _pick(pct_index)
            change = _pick(pct_index - 1 if pct_index is not None else None)
            close_price = _pick(pct_index - 2 if pct_index is not None else None)
            volume = _pick(pct_index + 1 if pct_index is not None else None)

            return StockRecord(
                stock_id=stock_id,
                stock_name=stock_name,
                close_price=close_price,
                change=change,
                change_pct=change_pct,
                volume=volume,
                category=category,
                source_url=source_url,
            )
        except Exception as exc:  # noqa: BLE001 - 單列失敗不可中斷整批
            logger.warning("failed to parse row %s: %s", cells, exc)
            return None

    def scrape_one(self, url: str, category: Optional[str] = None) -> List[StockRecord]:
        html = self._fetch_html(url)
        if html is None:
            return []
        records = self.parse_page(html, category=category, source_url=url)
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

    def save_json(self, records: List[StockRecord], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)
        logger.info("saved %d records to %s", len(records), path)

    def inspect_page(self, url: str, top_n: int = 5) -> None:
        html = self._fetch_html(url)
        if html is None:
            logger.error("could not fetch %s for inspection", url)
            return
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        logger.info("found %d tables on %s", len(tables), url)
        for i, table in enumerate(tables[:top_n]):
            print(f"--- table[{i}] ({len(table.find_all('tr'))} rows) ---")
            print(table.prettify()[:3000])


def rank_today_gainers(
    records: List[StockRecord], top_n: int = 10, reverse: bool = True
) -> List[StockRecord]:
    """依「當日」漲跌幅排序，僅反映已發生的數據，不涉及未來預測。"""
    ranked = [r for r in records if r.change_pct_float() is not None]
    ranked.sort(key=lambda r: r.change_pct_float(), reverse=reverse)
    return ranked[:top_n]


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

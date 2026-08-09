"""解析層：頁面解析、欄位映射、當日漲跌幅排序。"""
import logging
import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from logging_config import setup_logging
from models import StockRecord

setup_logging()
logger = logging.getLogger(__name__)

ID_NAME_PATTERNS = [
    re.compile(r"^(?P<id>\d{4,6})\s*(?P<name>\S+)$"),  # "2330 台積電"
    re.compile(r"^(?P<name>\S+?)\s*[\(（](?P<id>\d{4,6})[\)）]$"),  # "台積電(2330)"
]

HREF_ID_KEYS = ["code", "id", "stockid", "s", "a"]


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


def _parse_row(
    cells, category: Optional[str] = None, source_url: Optional[str] = None
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


def parse_page(
    html: str, category: Optional[str] = None, source_url: Optional[str] = None
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
        record = _parse_row(cells, category=category, source_url=source_url)
        if record is not None:
            records.append(record)
    return records


def rank_today_gainers(
    records: List[StockRecord], top_n: int = 10, reverse: bool = True
) -> List[StockRecord]:
    """依「當日」漲跌幅排序，僅反映已發生的數據，不涉及未來預測。"""
    ranked = [r for r in records if r.change_pct_float() is not None]
    ranked.sort(key=lambda r: r.change_pct_float(), reverse=reverse)
    return ranked[:top_n]

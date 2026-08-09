"""TradingView 報價層：批次取得即時（延遲）報價，取代/補齊 MoneyDJ 頁面的價格欄位。

用的是 TradingView 網頁版股票篩選器（screener）內部使用的端點，屬於未公開、
非官方文件化的介面：
- symbol-search.tradingview.com：代碼 → TradingView symbol（EXCHANGE:CODE）解析
- scanner.tradingview.com：批次查詢報價欄位

這兩個端點格式可能隨時變動，正式串接前務必先用 `debug_fetch_raw` 印出原始回應，
核對欄位名稱與 `QUOTE_FIELDS` 是否吻合，並自行確認 TradingView 使用條款、
避免高頻或大量請求。
"""
import logging
import time
from typing import Dict, List, Optional

import requests

from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

SYMBOL_SEARCH_URL = "https://symbol-search.tradingview.com/symbol_search/"
SCANNER_URL = "https://scanner.tradingview.com/taiwan/scan"

CANDIDATE_EXCHANGES = ["TWSE", "TPEX"]

# 依 close(收盤) / change(漲跌%) / change_abs(漲跌) / volume(成交量) 命名，
# 對應 TradingView screener 常見欄位；實際串接時請以 debug_fetch_raw 核對。
QUOTE_FIELDS = ["close", "change", "change_abs", "volume"]


def resolve_symbol(stock_id: str, timeout: int = 10) -> Optional[str]:
    """把台股代碼解析成 TradingView 的 EXCHANGE:CODE 格式（如 TWSE:2330）。"""
    try:
        resp = requests.get(
            SYMBOL_SEARCH_URL,
            params={"text": stock_id, "type": "stock", "exchange": "", "lang": "zh_TW"},
            timeout=timeout,
        )
        resp.raise_for_status()
        results = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("symbol search failed for %s: %s", stock_id, exc)
        return None

    for item in results:
        if item.get("symbol") == stock_id and item.get("exchange") in CANDIDATE_EXCHANGES:
            return f"{item['exchange']}:{item['symbol']}"
    return None


def resolve_symbols(
    stock_ids: List[str], delay: float = 0.3, timeout: int = 10
) -> Dict[str, str]:
    """逐一解析多個代碼，中間加小延遲避免過於頻繁。"""
    symbol_map: Dict[str, str] = {}
    for i, stock_id in enumerate(stock_ids):
        symbol = resolve_symbol(stock_id, timeout=timeout)
        if symbol:
            symbol_map[stock_id] = symbol
        else:
            logger.warning("could not resolve TradingView symbol for %s", stock_id)
        if i < len(stock_ids) - 1:
            time.sleep(delay)
    return symbol_map


def fetch_quotes(
    symbols: List[str], timeout: int = 10, batch_size: int = 50
) -> Dict[str, Dict[str, Optional[float]]]:
    """批次取得多檔 TradingView symbol 的報價（分批送出，避免單次請求過大）。"""
    quotes: Dict[str, Dict[str, Optional[float]]] = {}
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        payload = {"symbols": {"tickers": batch, "query": {"types": []}}, "columns": QUOTE_FIELDS}
        try:
            resp = requests.post(SCANNER_URL, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            logger.warning("scanner request failed for batch starting %s: %s", batch[0] if batch else "?", exc)
            continue
        for row in data.get("data", []):
            symbol = row.get("s")
            values = row.get("d", [])
            if symbol is None or len(values) < len(QUOTE_FIELDS):
                continue
            quotes[symbol] = dict(zip(QUOTE_FIELDS, values))
    return quotes


def apply_quote(record_dict: dict, quote: Optional[Dict[str, Optional[float]]]) -> dict:
    """把一筆 TradingView 報價套進 StockRecord 對應欄位的字典表示（純函式，方便測試）。

    找不到報價時原樣傳回，保留 MoneyDJ 解析出的既有數值作為備援。
    """
    if not quote:
        return record_dict
    close = quote.get("close")
    change_abs = quote.get("change_abs")
    change_pct = quote.get("change")
    volume = quote.get("volume")
    if close is not None:
        record_dict["close_price"] = f"{close:.2f}"
    if change_abs is not None:
        record_dict["change"] = f"{change_abs:+.2f}"
    if change_pct is not None:
        record_dict["change_pct"] = f"{change_pct:+.2f}%"
    if volume is not None:
        record_dict["volume"] = f"{int(volume):,}"
    return record_dict


def debug_fetch_raw(symbols: List[str], timeout: int = 10) -> None:
    """除錯工具：印出 scanner 端點的原始回應，供核對欄位名稱/格式用。"""
    payload = {"symbols": {"tickers": symbols, "query": {"types": []}}, "columns": QUOTE_FIELDS}
    resp = requests.post(SCANNER_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    print(resp.text)

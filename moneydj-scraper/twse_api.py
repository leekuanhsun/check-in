"""TWSE（台灣證券交易所）個股資訊層：日 K 線、三大法人買賣超、融資融券、基本資訊。

用的是 TWSE 官方公開資料端點（www.twse.com.tw 的 exchangeReport / fund 系列 JSON API），
比 tradingview.py 用的未公開端點來得穩定、有官方文件，但欄位順序、日期格式（民國年）、
回傳結構仍是依公開文件慣例撰寫，**尚未在可連外的環境對照過真實回應**。正式使用前請先用
`debug_fetch_raw` 印出原始 JSON，核對本檔案裡各函式解析用的欄位索引（`row[N]`）是否吻合，
不吻合要自行調整。

目前只涵蓋上市（TWSE）股票；上櫃（TPEX）股票的等效端點主機、路徑不同，本模組尚未支援，
遇到上櫃代碼時各函式會直接回傳空結果（不會拋例外，方便整批處理時跳過）。
"""
import logging
import time
from datetime import date, timedelta
from typing import Dict, List, Optional

import requests

from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
INSTITUTIONAL_URL = "https://www.twse.com.tw/fund/T86"
MARGIN_URL = "https://www.twse.com.tw/exchangeReport/MI_MARGN"
VALUATION_URL = "https://www.twse.com.tw/exchangeReport/BWIBBU_ALL"


def _roc_to_iso(roc_date: str) -> Optional[str]:
    """把 TWSE 回傳的民國年日期（如 "114/07/01"）轉成 ISO 格式 "2025-07-01"。"""
    try:
        y, m, d = str(roc_date).strip().split("/")
        return f"{int(y) + 1911:04d}-{int(m):02d}-{int(d):02d}"
    except (ValueError, AttributeError):
        return None


def _to_float(text) -> Optional[float]:
    if text is None:
        return None
    text = str(text).replace(",", "").strip()
    if text in ("", "--", "X", "N/A"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(text) -> Optional[int]:
    value = _to_float(text)
    return int(value) if value is not None else None


def fetch_stock_day(stock_id: str, year_month: str, timeout: int = 10) -> List[dict]:
    """取得單一股票單月的日 K 線（開高低收 + 成交量）。year_month 格式為 YYYYMM。

    官方欄位順序（依文件慣例）：日期,成交股數,成交金額,開盤價,最高價,最低價,收盤價,漲跌價差,成交筆數
    """
    try:
        resp = requests.get(
            STOCK_DAY_URL,
            params={"response": "json", "date": f"{year_month}01", "stockNo": stock_id},
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("stock_day fetch failed for %s %s: %s", stock_id, year_month, exc)
        return []

    if payload.get("stat") != "OK":
        return []

    return parse_stock_day(payload)


def parse_stock_day(payload: dict) -> List[dict]:
    """把 STOCK_DAY 端點的 JSON payload 轉成 [{date, open, high, low, close, volume}, ...]（純函式）。"""
    rows = []
    for row in payload.get("data", []):
        if len(row) < 7:
            continue
        iso_date = _roc_to_iso(row[0])
        if iso_date is None:
            continue
        rows.append(
            {
                "date": iso_date,
                "open": _to_float(row[3]),
                "high": _to_float(row[4]),
                "low": _to_float(row[5]),
                "close": _to_float(row[6]),
                "volume": _to_int(row[1]),
            }
        )
    return rows


def fetch_institutional_all(trade_date: date, timeout: int = 10) -> Dict[str, dict]:
    """取得某一日「全市場」三大法人買賣超，回傳依股票代碼索引的 dict。

    官方欄位（依文件慣例，節錄）：證券代號,證券名稱,外資買進股數,外資賣出股數,外資買賣超股數,
    外資自營商買進股數,外資自營商賣出股數,外資自營商買賣超股數,投信買進股數,投信賣出股數,
    投信買賣超股數,自營商買賣超股數(自行買賣),...,自營商買賣超股數,三大法人買賣超股數合計
    """
    date_str = trade_date.strftime("%Y%m%d")
    try:
        resp = requests.get(
            INSTITUTIONAL_URL,
            params={"response": "json", "date": date_str, "selectType": "ALL"},
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("institutional fetch failed for %s: %s", date_str, exc)
        return {}

    if payload.get("stat") != "OK":
        return {}

    return parse_institutional_all(payload, trade_date)


def parse_institutional_all(payload: dict, trade_date: date) -> Dict[str, dict]:
    """把 T86 端點的 JSON payload 轉成 {stock_id: {date, foreign, trust, dealer}}（純函式）。"""
    result: Dict[str, dict] = {}
    for row in payload.get("data", []):
        if len(row) < 11:
            continue
        stock_id = str(row[0]).strip()
        result[stock_id] = {
            "date": trade_date.isoformat(),
            "foreign": _to_int(row[4]),
            "trust": _to_int(row[10]),
            "dealer": _to_int(row[17]) if len(row) > 17 else None,
        }
    return result


def fetch_margin_all(trade_date: date, timeout: int = 10) -> Dict[str, dict]:
    """取得某一日「全市場」融資融券餘額，回傳依股票代碼索引的 dict。

    官方欄位（依文件慣例，節錄）：股票代號,股票名稱,融資買進,融資賣出,融資現金償還,
    融資前日餘額,融資今日餘額,融資限額,融券買進,融券賣出,融券現券償還,融券前日餘額,
    融券今日餘額,融券限額,資券互抵,註記
    """
    date_str = trade_date.strftime("%Y%m%d")
    try:
        resp = requests.get(
            MARGIN_URL,
            params={"response": "json", "date": date_str, "selectType": "ALL"},
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("margin fetch failed for %s: %s", date_str, exc)
        return {}

    return parse_margin_all(payload, trade_date)


def parse_margin_all(payload: dict, trade_date: date) -> Dict[str, dict]:
    """把 MI_MARGN 端點的 JSON payload 轉成 {stock_id: {...}}（純函式）。"""
    tables = payload.get("tables") or []
    data_rows = payload.get("data")
    if not data_rows and tables:
        data_rows = tables[0].get("data", [])
    data_rows = data_rows or []

    result: Dict[str, dict] = {}
    for row in data_rows:
        if len(row) < 13:
            continue
        stock_id = str(row[0]).strip()
        margin_balance = _to_int(row[6])
        margin_prev = _to_int(row[5])
        short_balance = _to_int(row[12])
        short_prev = _to_int(row[11])
        result[stock_id] = {
            "date": trade_date.isoformat(),
            "margin_balance": margin_balance,
            "margin_change": (
                margin_balance - margin_prev
                if margin_balance is not None and margin_prev is not None
                else None
            ),
            "short_balance": short_balance,
            "short_change": (
                short_balance - short_prev
                if short_balance is not None and short_prev is not None
                else None
            ),
        }
    return result


def fetch_valuation_all(timeout: int = 10) -> Dict[str, dict]:
    """取得全市場最新一筆本益比/殖利率/股價淨值比，回傳依股票代碼索引的 dict。

    官方欄位（依文件慣例，節錄）：證券代號,證券名稱,殖利率(%),股利年度,本益比,股價淨值比,...
    """
    try:
        resp = requests.get(VALUATION_URL, params={"response": "json"}, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("valuation fetch failed: %s", exc)
        return {}

    return parse_valuation_all(payload)


def parse_valuation_all(payload: dict) -> Dict[str, dict]:
    """把 BWIBBU_ALL 端點的 JSON payload 轉成 {stock_id: {pe_ratio, dividend_yield, pb_ratio}}（純函式）。"""
    result: Dict[str, dict] = {}
    for row in payload.get("data", []):
        if len(row) < 6:
            continue
        stock_id = str(row[0]).strip()
        result[stock_id] = {
            "dividend_yield": _to_float(row[2]),
            "pe_ratio": _to_float(row[4]),
            "pb_ratio": _to_float(row[5]),
        }
    return result


def _recent_weekdays(n: int, end_date: Optional[date] = None) -> List[date]:
    """回傳最近 n 個「非週末」日曆日（不排除國定假日，遇非交易日 API 會自然回傳空資料）。"""
    end_date = end_date or date.today()
    days: List[date] = []
    cursor = end_date
    while len(days) < n:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return sorted(days)


def _recent_months(n: int, end_date: Optional[date] = None) -> List[str]:
    end_date = end_date or date.today()
    months = []
    y, m = end_date.year, end_date.month
    for _ in range(n):
        months.append(f"{y:04d}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def fetch_stock_details(
    stock_ids: List[str],
    ohlc_months: int = 2,
    recent_days: int = 10,
    timeout: int = 10,
    delay: float = 0.3,
) -> Dict[str, dict]:
    """整合日 K 線、三大法人買賣超、融資融券、基本資訊，回傳依股票代碼索引的明細字典。

    每個交易日/月份只呼叫一次全市場端點，過濾出 stock_ids 需要的部分，
    避免對每檔股票重複打全市場 API；呼叫之間加小延遲，降低對官方伺服器的頻率。
    """
    stock_ids = list(dict.fromkeys(stock_ids))
    ohlc_by_stock: Dict[str, List[dict]] = {sid: [] for sid in stock_ids}
    institutional_by_stock: Dict[str, List[dict]] = {sid: [] for sid in stock_ids}
    margin_by_stock: Dict[str, List[dict]] = {sid: [] for sid in stock_ids}

    months = _recent_months(ohlc_months)
    for mi, ym in enumerate(months):
        for si, sid in enumerate(stock_ids):
            ohlc_by_stock[sid].extend(fetch_stock_day(sid, ym, timeout=timeout))
            if not (mi == len(months) - 1 and si == len(stock_ids) - 1):
                time.sleep(delay)

    days = _recent_weekdays(recent_days)
    for di, day in enumerate(days):
        day_institutional = fetch_institutional_all(day, timeout=timeout)
        day_margin = fetch_margin_all(day, timeout=timeout)
        for sid in stock_ids:
            if sid in day_institutional:
                institutional_by_stock[sid].append(day_institutional[sid])
            if sid in day_margin:
                margin_by_stock[sid].append(day_margin[sid])
        if di < len(days) - 1:
            time.sleep(delay)

    valuation = fetch_valuation_all(timeout=timeout)

    details: Dict[str, dict] = {}
    for sid in stock_ids:
        details[sid] = {
            "ohlc": sorted(ohlc_by_stock[sid], key=lambda r: r["date"]),
            "institutional": sorted(institutional_by_stock[sid], key=lambda r: r["date"]),
            "margin": sorted(margin_by_stock[sid], key=lambda r: r["date"]),
            "fundamentals": valuation.get(sid, {}),
        }
    return details


def debug_fetch_raw(url: str, params: dict, timeout: int = 10) -> None:
    """除錯工具：印出任一 TWSE 端點的原始回應，供核對欄位順序用。"""
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    print(resp.text)

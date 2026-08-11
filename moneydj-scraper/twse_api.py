"""TWSE（台灣證券交易所）個股資訊層：日 K 線、三大法人買賣超、融資融券、基本資訊。

用的是 TWSE 官方公開資料端點（www.twse.com.tw 的 exchangeReport / fund 系列 JSON API），
比 tradingview.py 用的未公開端點來得穩定、有官方文件。STOCK_DAY／T86／MI_MARGN／BWIBBU_ALL
四個端點的欄位順序與回傳結構已透過 GitHub Actions（有網路的環境）對照過真實回應並修正
（2026-08-11）：MI_MARGN 的個股資料實際包在 `tables` 陣列裡、且不是 `tables[0]`；
BWIBBU_ALL 只有 5 欄，不是原先假設的 6 欄；T86 的三大法人買賣超原始單位是「股」，
已在 `parse_institutional_all` 換算成「張」。日期解析（`_roc_to_iso`）也已驗證可正確處理
STOCK_DAY 回傳的民國年格式。若 TWSE 未來調整回應格式，可用 `debug_fetch_raw` 重新核對。

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

# 全市場端點：一次取得所有上市股票的基本資料／當日行情，避免對每檔股票各打一次 API。
# ALL_COMPANIES_URL 未曾在可連外環境驗證過欄位名稱，是依 TWSE OpenAPI（openapi.twse.com.tw）
# 慣例撰寫，正式使用前務必用 debug_fetch_raw 核對一次。
ALL_COMPANIES_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
ALL_STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL"


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


def _shares_to_lots(text) -> Optional[int]:
    """把股數換算成台灣慣用的「張」（1 張 = 1000 股，四捨五入）。"""
    value = _to_float(text)
    return round(value / 1000) if value is not None else None


def fetch_institutional_all(trade_date: date, timeout: int = 10) -> Dict[str, dict]:
    """取得某一日「全市場」三大法人買賣超，回傳依股票代碼索引的 dict。

    已對照真實回應驗證（2026-08-11）。官方欄位（單位：股）：
    證券代號,證券名稱,外陸資買進股數(不含外資自營商),外陸資賣出股數(不含外資自營商),
    外陸資買賣超股數(不含外資自營商),外資自營商買進股數,外資自營商賣出股數,外資自營商買賣超股數,
    投信買進股數,投信賣出股數,投信買賣超股數,自營商買賣超股數,自營商買進股數(自行買賣),
    自營商賣出股數(自行買賣),自營商買賣超股數(自行買賣),自營商買進股數(避險),自營商買進股數(避險),
    自營商買賣超股數(避險),三大法人買賣超股數
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
    """把 T86 端點的 JSON payload 轉成 {stock_id: {date, foreign, trust, dealer}}（純函式）。

    外資取「外陸資買賣超股數」（index 4），投信取「投信買賣超股數」（index 10），
    自營商取「自營商買賣超股數」合計欄（index 11，自行買賣+避險的加總，不是只取避險分項）。
    官方欄位單位是股，換算成張（÷1000）回傳，跟本專案 UI／insights 的「張」標示一致。
    """
    result: Dict[str, dict] = {}
    for row in payload.get("data", []):
        if len(row) < 19:
            continue
        stock_id = str(row[0]).strip()
        result[stock_id] = {
            "date": trade_date.isoformat(),
            "foreign": _shares_to_lots(row[4]),
            "trust": _shares_to_lots(row[10]),
            "dealer": _shares_to_lots(row[11]),
        }
    return result


def fetch_margin_all(trade_date: date, timeout: int = 10) -> Dict[str, dict]:
    """取得某一日「全市場」融資融券餘額，回傳依股票代碼索引的 dict。

    已對照真實回應驗證（2026-08-11）：資料包在 payload["tables"] 底下，含兩張表——
    一張是全市場信用交易統計（單列彙總，非個股），另一張才是逐檔個股資料
    （fields 以 "代號","名稱" 開頭），需要用 fields 判斷、挑出後者，不能假設固定在
    tables[0]（這正是先前版本回傳全空的原因：誤讀成彙總表，每列都因欄位數不足被跳過）。
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
    """把 MI_MARGN 端點的 JSON payload 轉成 {stock_id: {...}}（純函式）。

    個股資料所在的表格以 fields=["代號","名稱",...] 辨識，各表格在 tables 陣列裡的
    順序不保證固定，所以用欄位名稱搜尋而非寫死索引。
    """
    tables = payload.get("tables") or []
    stock_table = None
    for t in tables:
        fields = t.get("fields") or []
        if len(fields) >= 2 and fields[0] == "代號" and fields[1] == "名稱":
            stock_table = t
            break
    if stock_table is None:
        return {}

    result: Dict[str, dict] = {}
    for row in stock_table.get("data", []):
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

    已對照真實回應驗證（2026-08-11）。官方欄位（共 5 欄）：
    股票代號,股票名稱,本益比,殖利率(%),股價淨值比。虧損公司本益比常回傳 "-"，
    _to_float 會把它當成無法解析、安全回傳 None。
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
        if len(row) < 5:
            continue
        stock_id = str(row[0]).strip()
        result[stock_id] = {
            "pe_ratio": _to_float(row[2]),
            "dividend_yield": _to_float(row[3]),
            "pb_ratio": _to_float(row[4]),
        }
    return result


def fetch_all_companies(timeout: int = 15) -> Dict[str, dict]:
    """取得全部上市公司基本資料（含官方產業別分類），回傳依股票代碼索引的 dict。

    **尚未在可連外環境對照過真實回應**——依 TWSE OpenAPI（openapi.twse.com.tw）文件慣例
    撰寫，欄位名稱可能與實際回應不同，正式使用前務必用 debug_fetch_raw 核對一次。
    """
    try:
        resp = requests.get(ALL_COMPANIES_URL, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("fetch_all_companies failed: %s", exc)
        return {}

    return parse_all_companies(payload)


def parse_all_companies(payload) -> Dict[str, dict]:
    """把 t187ap03_L 端點的 JSON payload 轉成 {stock_id: {name, industry}}（純函式）。

    OpenAPI 慣例回傳「list of dict」（每筆一個物件），不是舊版 exchangeReport 那種
    「欄位陣列 + 資料列陣列」的表格格式，所以用 dict.get() 依鍵名取值，不是用索引。
    """
    if not isinstance(payload, list):
        return {}
    result: Dict[str, dict] = {}
    for row in payload:
        if not isinstance(row, dict):
            continue
        stock_id = str(row.get("公司代號") or row.get("出表日期") or "").strip()
        if not stock_id:
            continue
        result[stock_id] = {
            "name": (row.get("公司簡稱") or row.get("公司名稱") or "").strip() or None,
            "industry": (row.get("產業別") or "").strip() or None,
        }
    return result


def fetch_all_stock_day(timeout: int = 15) -> Dict[str, dict]:
    """取得全部上市股票「當日」的收盤/漲跌/成交量，一次呼叫涵蓋所有股票，不逐檔查詢。

    **尚未在可連外環境對照過真實回應**——依 STOCK_DAY 的欄位順序慣例類推撰寫，
    正式使用前務必用 debug_fetch_raw 核對一次。
    """
    try:
        resp = requests.get(ALL_STOCK_DAY_URL, params={"response": "json"}, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("fetch_all_stock_day failed: %s", exc)
        return {}

    return parse_all_stock_day(payload)


def parse_all_stock_day(payload: dict) -> Dict[str, dict]:
    """把 STOCK_DAY_ALL 端點的 JSON payload 轉成 {stock_id: {name, close, change, volume}}（純函式）。

    假設欄位順序跟單檔 STOCK_DAY 類似（證券代號,證券名稱,成交股數,...,收盤價,漲跌價差,...），
    但這是全市場版本，實際欄位順序/數量可能不同，需以 debug_fetch_raw 核對。
    """
    result: Dict[str, dict] = {}
    for row in payload.get("data", []):
        if len(row) < 9:
            continue
        stock_id = str(row[0]).strip()
        close = _to_float(row[7])
        change = _to_float(row[8])
        result[stock_id] = {
            "name": str(row[1]).strip() or None,
            "close": close,
            "change": change,
            "volume": _to_int(row[2]),
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

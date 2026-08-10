"""測試 twse_api.py 的純解析函式。

注意：以下 fixture JSON 是依 twse_api.py 內文件註解描述的欄位順序手動建構，用來驗證
「本模組的解析邏輯本身自洽」，不代表已對照過 TWSE 真實回應（這個環境無法連線驗證，
見 README 的已知限制）。串接真實資料前務必用 debug_fetch_raw 核對一次。
"""
from datetime import date

from twse_api import (
    _recent_months,
    _recent_weekdays,
    _roc_to_iso,
    _to_float,
    _to_int,
    parse_institutional_all,
    parse_margin_all,
    parse_stock_day,
    parse_valuation_all,
)


def test_roc_to_iso():
    assert _roc_to_iso("114/07/01") == "2025-07-01"
    assert _roc_to_iso("99/01/05") == "2010-01-05"
    assert _roc_to_iso("not-a-date") is None
    assert _roc_to_iso(None) is None


def test_to_float_and_to_int():
    assert _to_float("1,234.56") == 1234.56
    assert _to_float("--") is None
    assert _to_float("X") is None
    assert _to_float(None) is None
    assert _to_int("12,345") == 12345
    assert _to_int("--") is None


def test_parse_stock_day():
    payload = {
        "stat": "OK",
        "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
        "data": [
            ["114/07/01", "25,123,456", "23,000,000,000", "940.00", "955.00", "935.00", "950.00", "+5.00", "12,345"],
            ["114/07/02", "18,000,000", "17,000,000,000", "950.00", "960.00", "945.00", "958.00", "+8.00", "9,000"],
        ],
    }
    rows = parse_stock_day(payload)
    assert len(rows) == 2
    assert rows[0] == {
        "date": "2025-07-01",
        "open": 940.0,
        "high": 955.0,
        "low": 935.0,
        "close": 950.0,
        "volume": 25123456,
    }
    assert rows[1]["date"] == "2025-07-02"


def test_parse_stock_day_skips_malformed_rows():
    payload = {"data": [["114/07/01", "1"], ["bad-date", "1", "2", "3", "4", "5", "6"]]}
    assert parse_stock_day(payload) == []


def test_parse_institutional_all():
    row = ["2330", "台積電"] + ["0"] * 2 + ["1,234"] + ["0"] * 5 + ["-200"] + ["0"] * 6 + ["50"]
    payload = {"stat": "OK", "data": [row]}
    result = parse_institutional_all(payload, date(2026, 8, 5))
    assert result["2330"]["date"] == "2026-08-05"
    assert result["2330"]["foreign"] == 1234
    assert result["2330"]["trust"] == -200
    assert result["2330"]["dealer"] == 50


def test_parse_margin_all():
    row = ["2330", "台積電", "100", "50", "0", "10000", "10050", "999999", "20", "30", "0", "3000", "2990", "9999"]
    payload = {"data": [row]}
    result = parse_margin_all(payload, date(2026, 8, 5))
    assert result["2330"] == {
        "date": "2026-08-05",
        "margin_balance": 10050,
        "margin_change": 50,
        "short_balance": 2990,
        "short_change": -10,
    }


def test_parse_valuation_all():
    payload = {"data": [["2330", "台積電", "1.8", "2025", "18.5", "5.6"]]}
    result = parse_valuation_all(payload)
    assert result["2330"] == {"dividend_yield": 1.8, "pe_ratio": 18.5, "pb_ratio": 5.6}


def test_recent_weekdays_excludes_weekends():
    # 2026-08-10 is a Monday
    days = _recent_weekdays(5, end_date=date(2026, 8, 10))
    assert len(days) == 5
    assert all(d.weekday() < 5 for d in days)
    assert days == sorted(days)
    assert days[-1] == date(2026, 8, 10)


def test_recent_months_wraps_year_boundary():
    months = _recent_months(3, end_date=date(2026, 1, 15))
    assert months == ["202511", "202512", "202601"]

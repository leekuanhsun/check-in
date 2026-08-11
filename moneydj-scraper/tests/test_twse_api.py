"""測試 twse_api.py 的純解析函式。

fixture 資料取自 2026-08-11 透過 GitHub Actions（有網路的環境）對 TWSE 真實端點的實際
回應（見 debug_endpoints.py 的除錯輸出），不是憑文件猜的欄位順序。
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
    # 2026-08-10 對 2330 的真實 T86 回應列（19 欄，單位：股）
    row = [
        "2330", "台積電          ", "13,479,627", "13,360,531", "119,096",
        "0", "0", "0", "251,132", "98,503", "152,629", "448,255",
        "394,050", "79,163", "314,887", "301,245", "167,877", "133,368", "719,980",
    ]
    payload = {"stat": "OK", "data": [row]}
    result = parse_institutional_all(payload, date(2026, 8, 10))
    assert result["2330"]["date"] == "2026-08-10"
    # 股轉張：119,096 / 1000 -> 119；152,629 / 1000 -> 153；448,255 / 1000 -> 448
    assert result["2330"]["foreign"] == 119
    assert result["2330"]["trust"] == 153
    assert result["2330"]["dealer"] == 448


def test_parse_margin_all():
    # 真實回應把個股資料放在 tables[1]（tables[0] 是全市場單列彙總），
    # 用 fields 判斷、不是寫死 tables[0]／tables[1] 的位置
    payload = {
        "stat": "OK",
        "tables": [
            {
                "title": "115年08月10日 信用交易統計",
                "fields": ["項目", "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額"],
                "data": [["融資(交易單位)", "436,013", "412,135", "7,092", "8,986,437", "9,003,223"]],
            },
            {
                "title": "115年08月10日 融資融券彙總 (全部)",
                "fields": [
                    "代號", "名稱", "買進", "賣出", "現金償還", "前日餘額", "今日餘額", "次一營業日限額",
                    "買進", "賣出", "現券償還", "前日餘額", "今日餘額", "次一營業日限額", "資券互抵", "註記",
                ],
                "data": [
                    ["2330", "台積電", "100", "50", "0", "10000", "10050", "999999",
                     "20", "30", "0", "3000", "2990", "9999", "0", " "],
                ],
            },
        ],
    }
    result = parse_margin_all(payload, date(2026, 8, 10))
    assert result["2330"] == {
        "date": "2026-08-10",
        "margin_balance": 10050,
        "margin_change": 50,
        "short_balance": 2990,
        "short_change": -10,
    }


def test_parse_margin_all_no_matching_table_returns_empty():
    payload = {"tables": [{"fields": ["項目", "買進"], "data": [["x", "1"]]}]}
    assert parse_margin_all(payload, date(2026, 8, 10)) == {}


def test_parse_valuation_all():
    # 真實 BWIBBU_ALL 只有 5 欄；本益比虧損股常見回傳 "-"
    payload = {
        "fields": ["股票代號", "股票名稱", "本益比", "殖利率(%)", "股價淨值比"],
        "data": [
            ["1101", "台泥", "-", "3.26", "0.78"],
            ["2330", "台積電", "18.5", "1.8", "5.6"],
        ],
    }
    result = parse_valuation_all(payload)
    assert result["1101"] == {"pe_ratio": None, "dividend_yield": 3.26, "pb_ratio": 0.78}
    assert result["2330"] == {"pe_ratio": 18.5, "dividend_yield": 1.8, "pb_ratio": 5.6}


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

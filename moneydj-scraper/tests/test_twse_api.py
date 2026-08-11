"""測試 twse_api.py 的純解析函式。

fixture 資料取自 2026-08-11 透過 GitHub Actions（有網路的環境）對 TWSE 真實端點的實際
回應（見 debug_endpoints.py / debug_universe_endpoints.py 的除錯輸出），不是憑文件猜的
欄位順序。
"""
from datetime import date

from twse_api import (
    _recent_months,
    _recent_weekdays,
    _roc_to_iso,
    _to_float,
    _to_int,
    parse_all_companies,
    parse_all_stock_day,
    parse_institutional_all,
    parse_instrument_types,
    parse_margin_all,
    parse_market_ohlc_all,
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


def test_parse_market_ohlc_all():
    # 真實回應（2026-08-06）：個股「每日收盤行情」表格藏在 tables 陣列裡（同一天還有
    # 大盤指數、成交統計等其他表格），用 fields 判斷，不是固定索引位置。
    payload = {
        "tables": [
            {
                "title": "115年08月06日 價格指數(臺灣證券交易所)",
                "fields": ["指數", "收盤指數", "漲跌(+/-)", "漲跌點數", "漲跌百分比(%)", "特殊處理註記"],
                "data": [["寶島股價指數", "49,294.46", "-", "155.80", "-0.32", ""]],
            },
            {
                "title": "115年08月06日 每日收盤行情(全部(不含權證、牛熊證、可展延牛熊證))",
                "fields": [
                    "證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價",
                    "最低價", "收盤價", "漲跌(+/-)", "漲跌價差", "最後揭示買價", "最後揭示買量",
                    "最後揭示賣價", "最後揭示賣量", "本益比",
                ],
                "data": [
                    ["00400A", "主動國泰動能高息", "37,160,775", "6,993", "511,633,219",
                     "13.65", "13.91", "13.51", "13.89", "+", "0.20", "13.89", "131", "13.90", "306", "0.00"],
                ],
            },
        ],
    }
    result = parse_market_ohlc_all(payload, date(2026, 8, 6))
    assert result["00400A"] == {
        "date": "2026-08-06",
        "open": 13.65,
        "high": 13.91,
        "low": 13.51,
        "close": 13.89,
        "volume": 37160775,
    }


def test_parse_market_ohlc_all_no_matching_table_returns_empty():
    payload = {"tables": [{"fields": ["指數", "收盤指數"], "data": [["x", "1"]]}]}
    assert parse_market_ohlc_all(payload, date(2026, 8, 6)) == {}


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


def test_parse_all_companies():
    # 真實 t187ap03_L 回應節錄（2026-08-11）：產業別是數字代碼，不是文字
    payload = [
        {"公司代號": "2330", "公司簡稱": "台積電", "產業別": "24"},
        {"公司代號": "2317", "公司簡稱": "鴻海", "產業別": "31"},
        {"公司代號": "1101", "公司簡稱": "台泥", "產業別": "01"},
        {"公司代號": "9999", "公司簡稱": "未知代碼測試", "產業別": "99"},
    ]
    result = parse_all_companies(payload)
    assert result["2330"] == {"name": "台積電", "industry": "半導體業"}
    assert result["2317"] == {"name": "鴻海", "industry": "其他電子業"}
    assert result["1101"] == {"name": "台泥", "industry": "水泥工業"}
    assert result["9999"] == {"name": "未知代碼測試", "industry": "產業別代碼 99"}


def test_parse_all_companies_skips_non_list_payload():
    assert parse_all_companies({"data": []}) == {}
    assert parse_all_companies(None) == {}


def test_parse_all_companies_skips_rows_without_stock_id():
    payload = [{"公司簡稱": "缺代號"}, {"公司代號": "1234", "公司簡稱": "有代號", "產業別": "20"}]
    result = parse_all_companies(payload)
    assert list(result.keys()) == ["1234"]
    assert result["1234"]["industry"] == "其他業"


def test_parse_all_stock_day():
    # 真實 STOCK_DAY_ALL（OpenAPI 版）回應節錄（2026-08-11）：list of dict，英文鍵名
    payload = [
        {
            "Date": "1150810", "Code": "2330", "Name": "台積電",
            "TradeVolume": "21498241", "TradeValue": "50000000000",
            "OpeningPrice": "2390.00", "HighestPrice": "2410.00", "LowestPrice": "2380.00",
            "ClosingPrice": "2380.00", "Change": "10.0000", "Transaction": "20000",
        },
        {
            "Date": "1150810", "Code": "2317", "Name": "鴻海",
            "TradeVolume": "34854398", "TradeValue": "9000000000",
            "OpeningPrice": "260.00", "HighestPrice": "266.00", "LowestPrice": "259.00",
            "ClosingPrice": "264.50", "Change": "-4.5000", "Transaction": "15000",
        },
    ]
    result = parse_all_stock_day(payload)
    assert result["2330"] == {"name": "台積電", "close": 2380.0, "change": 10.0, "volume": 21498241}
    assert result["2317"]["change"] == -4.5


def test_parse_all_stock_day_skips_non_list_payload():
    assert parse_all_stock_day({"data": []}) == {}
    assert parse_all_stock_day(None) == {}


def test_parse_all_stock_day_skips_rows_without_code():
    payload = [{"Name": "缺代碼"}, {"Code": "1234", "Name": "有代碼", "ClosingPrice": "10.00"}]
    result = parse_all_stock_day(payload)
    assert list(result.keys()) == ["1234"]


def _isin_html_fixture() -> bytes:
    """跟 ISIN strMode=2 真實回應同結構的最小 fixture（欄位、分類標題列順序取自
    2026-08-11 debug_isin.py 對照真實回應的輸出）。"""
    html = (
        "<table><tr>"
        "<td>有價證券代號及名稱</td><td>國際證券辨識號碼(ISIN Code)</td><td>上市日</td>"
        "<td>市場別</td><td>產業別</td><td>CFICode</td><td>備註</td>"
        "</tr>"
        "<tr><td colspan=7>股票</td></tr>"
        "<tr><td>2330　台積電</td><td>TW0002330008</td><td>1994/09/05</td>"
        "<td>上市</td><td>半導體業</td><td>ESVUFR</td><td></td></tr>"
        "<tr><td colspan=7>ETF</td></tr>"
        "<tr><td>0050　元大台灣50</td><td>TW0000050004</td><td>2003/06/30</td>"
        "<td>上市</td><td></td><td>CEOGEU</td><td></td></tr>"
        "<tr><td>00400A　主動國泰動能高息</td><td>TW00000400A3</td><td>2026/04/09</td>"
        "<td>上市</td><td></td><td>CEOJEU</td><td></td></tr>"
        "<tr><td colspan=7>ETN</td></tr>"
        "<tr><td>020000　富邦特選蘋果N</td><td>TW0000200005</td><td>2019/04/30</td>"
        "<td>上市</td><td></td><td>CMXXXU</td><td></td></tr>"
        "<tr><td colspan=7>受益證券-不動產投資信託</td></tr>"
        "<tr><td>01001T　土銀富邦R1</td><td>TW00001001T8</td><td>2005/03/10</td>"
        "<td>上市</td><td></td><td>CBCIXU</td><td></td></tr>"
        "</table>"
    )
    return html.encode("big5")


def test_parse_instrument_types():
    result = parse_instrument_types(_isin_html_fixture())
    assert result == {
        "2330": "股票",
        "0050": "ETF",
        "00400A": "ETF",
        "020000": "ETN",
        "01001T": "受益證券-不動產投資信託",
    }


def test_parse_instrument_types_empty_html():
    assert parse_instrument_types(b"<table></table>") == {}

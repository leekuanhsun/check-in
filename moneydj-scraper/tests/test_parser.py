import pytest

from models import StockRecord
from parser import (
    _extract_id_from_href,
    _split_id_and_name,
    parse_page,
    rank_today_gainers,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2330 台積電", ("2330", "台積電")),
        ("台積電(2330)", ("2330", "台積電")),
        ("台積電（2330）", ("2330", "台積電")),
        ("無代碼文字", (None, "無代碼文字")),
        ("", (None, None)),
    ],
)
def test_split_id_and_name(text, expected):
    assert _split_id_and_name(text) == expected


@pytest.mark.parametrize(
    "href, expected",
    [
        ("zca_0.djhtm?a=2330", "2330"),
        ("/z/zc/zca/zca_0.djhtm?code=2454&x=1", "2454"),
        ("/foo/2317/bar", "2317"),
        ("/foo/bar", None),
        ("", None),
    ],
)
def test_extract_id_from_href(href, expected):
    assert _extract_id_from_href(href) == expected


def test_change_pct_float():
    assert StockRecord(stock_id="1", stock_name="A", change_pct="+2.50%").change_pct_float() == 2.5
    assert StockRecord(stock_id="1", stock_name="A", change_pct="-1.20%").change_pct_float() == -1.2
    assert StockRecord(stock_id="1", stock_name="A", change_pct="bad").change_pct_float() is None
    assert StockRecord(stock_id="1", stock_name="A", change_pct=None).change_pct_float() is None


def test_rank_today_gainers():
    records = [
        StockRecord(stock_id="1", stock_name="A", change_pct="+1.0%"),
        StockRecord(stock_id="2", stock_name="B", change_pct="+5.0%"),
        StockRecord(stock_id="3", stock_name="C", change_pct="-2.0%"),
        StockRecord(stock_id="4", stock_name="D", change_pct="bad"),
    ]
    top = rank_today_gainers(records, top_n=2)
    assert [r.stock_id for r in top] == ["2", "1"]

    bottom = rank_today_gainers(records, top_n=1, reverse=False)
    assert [r.stock_id for r in bottom] == ["3"]


def test_parse_page_basic_table():
    html = """
    <table>
    <tr><th>股票</th><th>收盤</th><th>漲跌</th><th>漲跌%</th><th>成交量</th></tr>
    <tr><td>2330 台積電</td><td>950</td><td>+10</td><td>+1.06%</td><td>30000</td></tr>
    <tr><td>2454 聯發科</td><td>1200</td><td>-20</td><td>-1.64%</td><td>5000</td></tr>
    </table>
    """
    records = parse_page(html, category="test", source_url="http://x")
    assert len(records) == 2
    assert records[0].stock_id == "2330"
    assert records[0].stock_name == "台積電"
    assert records[0].change_pct == "+1.06%"
    assert records[0].category == "test"
    assert records[1].stock_id == "2454"
    assert records[1].change_pct == "-1.64%"


def test_parse_page_falls_back_to_href_for_id():
    html = """
    <table>
    <tr><td><a href="detail.djhtm?a=2603">長榮</a></td><td>150</td><td>+3</td><td>+2.04%</td></tr>
    <tr><td><a href="detail.djhtm?a=2609">陽明</a></td><td>90</td><td>-1</td><td>-1.10%</td></tr>
    </table>
    """
    records = parse_page(html)
    assert len(records) == 2
    assert records[0].stock_id == "2603"
    assert records[1].stock_id == "2609"


def test_parse_page_no_table_returns_empty():
    assert parse_page("<html><body>no tables here</body></html>") == []

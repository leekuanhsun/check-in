from aggregate import summarize_by_stock
from models import StockRecord


def test_summarize_counts_distinct_sites_for_same_stock():
    records = [
        StockRecord(
            stock_id="2330", stock_name="台積電", category="輝達概念股",
            close_price="950", change_pct="+1.0%", source_url="https://site-a.example/nvda",
        ),
        StockRecord(
            stock_id="2330", stock_name="台積電", category="輝達概念股",
            close_price="951", change_pct="+1.1%", source_url="https://site-b.example/nvda",
        ),
        StockRecord(
            stock_id="2454", stock_name="聯發科", category="蘋果概念股",
            close_price="1200", change_pct="-0.5%", source_url="https://site-a.example/aapl",
        ),
    ]
    summary = summarize_by_stock(records)

    tsmc = next(s for s in summary if s["stock_id"] == "2330")
    assert tsmc["source_count"] == 2
    assert tsmc["sites"] == ["site-a.example", "site-b.example"]
    assert tsmc["categories"] == ["輝達概念股"]
    assert tsmc["latest_close_price"] == "951"  # last-seen wins

    mtk = next(s for s in summary if s["stock_id"] == "2454")
    assert mtk["source_count"] == 1


def test_summarize_sorts_by_source_count_desc_then_stock_id():
    records = [
        StockRecord(stock_id="3", stock_name="C", source_url="https://a.example/x"),
        StockRecord(stock_id="1", stock_name="A", source_url="https://a.example/x"),
        StockRecord(stock_id="1", stock_name="A", source_url="https://b.example/x"),
    ]
    summary = summarize_by_stock(records)
    assert [s["stock_id"] for s in summary] == ["1", "3"]


def test_summarize_skips_records_without_stock_id():
    records = [StockRecord(stock_id=None, stock_name="無代碼")]
    assert summarize_by_stock(records) == []


def test_summarize_merges_multiple_categories_for_same_stock():
    records = [
        StockRecord(stock_id="2330", stock_name="台積電", category="輝達概念股", source_url="https://a.example/x"),
        StockRecord(stock_id="2330", stock_name="台積電", category="AI 伺服器供應鏈", source_url="https://a.example/y"),
    ]
    summary = summarize_by_stock(records)
    assert summary[0]["categories"] == ["AI 伺服器供應鏈", "輝達概念股"]

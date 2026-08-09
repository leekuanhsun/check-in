from tradingview import apply_quote


def test_apply_quote_overwrites_price_fields():
    record = {
        "stock_id": "2330",
        "stock_name": "台積電",
        "close_price": "999.00",
        "change": "+0.00",
        "change_pct": "+0.00%",
        "volume": "0",
    }
    quote = {"close": 950.5, "change_abs": -12.5, "change": -1.3, "volume": 30125}
    updated = apply_quote(record, quote)
    assert updated["close_price"] == "950.50"
    assert updated["change"] == "-12.50"
    assert updated["change_pct"] == "-1.30%"
    assert updated["volume"] == "30,125"


def test_apply_quote_no_quote_keeps_original():
    record = {"stock_id": "2330", "close_price": "950.00"}
    assert apply_quote(dict(record), None) == record
    assert apply_quote(dict(record), {}) == record


def test_apply_quote_partial_quote_only_overwrites_present_fields():
    record = {"close_price": "100.00", "change": "+1.00", "change_pct": "+1.00%", "volume": "500"}
    quote = {"close": 105.0, "change_abs": None, "change": None, "volume": None}
    updated = apply_quote(dict(record), quote)
    assert updated["close_price"] == "105.00"
    assert updated["change"] == "+1.00"
    assert updated["change_pct"] == "+1.00%"
    assert updated["volume"] == "500"

from insights import summarize_stock_insights


def _ohlc(closes):
    return [{"date": f"2026-01-{i+1:02d}", "close": c} for i, c in enumerate(closes)]


def test_empty_inputs_return_no_bullets():
    assert summarize_stock_insights([], [], []) == []


def test_price_trend_bullets_and_ma_position():
    closes = [100, 101, 102, 103, 104, 105, 106]  # 7 days, rising
    bullets = summarize_stock_insights(_ohlc(closes), [], [])
    joined = " ".join(bullets)
    assert "近 5 個交易日股價上漲" in joined
    assert "5 日均價" in joined
    assert "之上" in joined
    assert "免責" not in joined  # no literal word but disclaimer line should still be last
    assert bullets[-1].startswith("以上僅為歷史數據統計整理")


def test_price_decline_direction():
    closes = [110, 108, 106, 104, 102, 100]
    bullets = summarize_stock_insights(_ohlc(closes), [], [])
    assert any("下跌" in b for b in bullets)


def test_20_day_bullet_requires_21_points():
    closes = list(range(100, 100 + 20))  # 20 points, not enough for 20d comparison
    bullets = summarize_stock_insights(_ohlc(closes), [], [])
    assert not any("20 個交易日" in b for b in bullets)

    closes21 = list(range(100, 100 + 21))
    bullets21 = summarize_stock_insights(_ohlc(closes21), [], [])
    assert any("20 個交易日" in b for b in bullets21)


def test_institutional_bullets_sum_and_direction():
    institutional = [
        {"date": "2026-08-03", "foreign": 500, "trust": -100},
        {"date": "2026-08-04", "foreign": -200, "trust": -50},
        {"date": "2026-08-05", "foreign": 300, "trust": 20},
    ]
    bullets = summarize_stock_insights([], institutional, [])
    joined = " ".join(bullets)
    assert "外資近 3 個交易日累計買超 600 張" in joined
    assert "投信近 3 個交易日累計賣超 130 張" in joined


def test_margin_bullets_use_first_and_last():
    margin = [
        {"date": "2026-08-03", "margin_balance": 1000, "short_balance": 500},
        {"date": "2026-08-04", "margin_balance": 1050, "short_balance": 480},
        {"date": "2026-08-05", "margin_balance": 900, "short_balance": 520},
    ]
    bullets = summarize_stock_insights([], [], margin)
    joined = " ".join(bullets)
    assert "融資餘額較 3 個交易日前減少 100 張" in joined
    assert "融券餘額較 3 個交易日前增加 20 張" in joined


def test_margin_with_single_point_produces_no_bullet():
    margin = [{"date": "2026-08-05", "margin_balance": 1000, "short_balance": 500}]
    assert summarize_stock_insights([], [], margin) == []


def test_disclaimer_only_appears_when_there_is_content():
    assert summarize_stock_insights([], [], []) == []
    assert summarize_stock_insights(_ohlc([100]), [], []) != []

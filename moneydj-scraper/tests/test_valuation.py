from valuation import (
    compute_eps,
    industry_median_pe,
    recommended_buy_price,
    valuation_gap_pct,
)


def test_compute_eps_basic():
    # PE = price / EPS -> EPS = price / PE
    assert compute_eps(100.0, 20.0) == 5.0


def test_compute_eps_missing_inputs_returns_none():
    assert compute_eps(None, 20.0) is None
    assert compute_eps(100.0, None) is None


def test_compute_eps_non_positive_pe_returns_none():
    # loss-making companies commonly report negative or zero PE
    assert compute_eps(100.0, -5.0) is None
    assert compute_eps(100.0, 0.0) is None


def test_industry_median_pe_basic():
    records = [
        {"category": "半導體業", "pe_ratio": 10.0},
        {"category": "半導體業", "pe_ratio": 20.0},
        {"category": "半導體業", "pe_ratio": 30.0},
        {"category": "食品工業", "pe_ratio": 15.0},
    ]
    result = industry_median_pe(records, min_peers=3)
    assert result["半導體業"] == 20.0
    assert "食品工業" not in result  # only 1 peer, below min_peers


def test_industry_median_pe_ignores_non_positive_pe():
    records = [
        {"category": "生技醫療業", "pe_ratio": -10.0},  # loss-making, excluded
        {"category": "生技醫療業", "pe_ratio": 10.0},
        {"category": "生技醫療業", "pe_ratio": 20.0},
        {"category": "生技醫療業", "pe_ratio": 30.0},
    ]
    result = industry_median_pe(records, min_peers=3)
    assert result["生技醫療業"] == 20.0


def test_industry_median_pe_skips_missing_category():
    records = [{"category": None, "pe_ratio": 10.0}, {"category": "", "pe_ratio": 10.0}]
    assert industry_median_pe(records, min_peers=1) == {}


def test_recommended_buy_price_applies_margin_of_safety():
    # eps=5, industry_pe=20 -> fair value = 100, with 0.9 margin -> 90
    assert recommended_buy_price(5.0, 20.0, margin_of_safety=0.9) == 90.0


def test_recommended_buy_price_missing_inputs_returns_none():
    assert recommended_buy_price(None, 20.0) is None
    assert recommended_buy_price(5.0, None) is None
    assert recommended_buy_price(-5.0, 20.0) is None


def test_valuation_gap_pct_overpriced():
    # current price 110 vs recommended 100 -> 10% overpriced
    assert valuation_gap_pct(110.0, 100.0) == 10.0


def test_valuation_gap_pct_underpriced():
    assert valuation_gap_pct(90.0, 100.0) == -10.0


def test_valuation_gap_pct_missing_inputs_returns_none():
    assert valuation_gap_pct(None, 100.0) is None
    assert valuation_gap_pct(100.0, None) is None
    assert valuation_gap_pct(100.0, 0.0) is None

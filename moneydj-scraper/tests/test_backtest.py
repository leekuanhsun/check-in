from backtest import _zscore_cross_section, composite_scores, run_backtest


def test_zscore_cross_section_basic():
    raw = {"A": 1.0, "B": 2.0, "C": 3.0}
    z = _zscore_cross_section(raw, min_count=3)
    assert z["A"] < z["B"] < z["C"]
    assert abs(sum(z.values())) < 1e-9  # mean-centered


def test_zscore_cross_section_too_few_values_returns_empty():
    raw = {"A": 1.0, "B": None, "C": None}
    assert _zscore_cross_section(raw, min_count=3) == {}


def test_zscore_cross_section_zero_std_returns_empty():
    raw = {"A": 5.0, "B": 5.0, "C": 5.0}
    assert _zscore_cross_section(raw, min_count=3) == {}


def test_composite_scores_weighted_average_ignores_missing_factors():
    # Need >= min_count (20) valid values per factor for _zscore_cross_section to
    # activate at all; build 25 stocks where one factor has a missing value for "S00".
    stock_ids = [f"S{i:02d}" for i in range(25)]
    f1 = {sid: float(i) for i, sid in enumerate(stock_ids)}
    f2 = {sid: float(i) for i, sid in enumerate(stock_ids)}
    f2["S00"] = None  # missing for the lowest-ranked stock on f1

    composite = composite_scores({"f1": f1, "f2": f2}, {"f1": 1.0, "f2": 1.0})

    assert "S00" in composite  # still scored using f1 alone, not dropped
    assert "S24" in composite
    # S24 has the highest f1 and f2 values -> should have the highest composite score
    assert composite["S24"] == max(composite.values())


def _make_stock(closes, foreign_flows=None, start_date="2026-01-01"):
    import datetime

    base = datetime.date.fromisoformat(start_date)
    ohlc = []
    institutional = []
    for i, c in enumerate(closes):
        d = (base + datetime.timedelta(days=i)).isoformat()
        ohlc.append({"date": d, "open": c, "high": c, "low": c, "close": c, "volume": 1000})
        if foreign_flows is not None and i < len(foreign_flows):
            institutional.append({"date": d, "foreign": foreign_flows[i], "trust": 0, "dealer": 0})
    return {"ohlc": ohlc, "institutional": institutional, "margin": [], "fundamentals": {}}


def test_run_backtest_long_leg_beats_short_leg_when_momentum_persists():
    # Build a small universe: half the stocks trend up strongly and keep trending up,
    # the other half trend down and keep trending down. Isolate the momentum factor
    # (weight-only momentum_20) so the test verifies the walk-forward mechanics work
    # correctly, without the reversal factor fighting it — a strictly monotonic trend
    # saturates RSI at 100/0, which makes the reversal (mean-reversion) factor flag
    # the *opposite* side on purpose; that's expected factor behavior, not something
    # this mechanics test should have to fight.
    detail = {}
    n_days = 40
    for i in range(15):
        closes = [100 * (1.01 ** d) for d in range(n_days)]
        detail[f"UP{i}"] = _make_stock(closes)
    for i in range(15):
        closes = [100 * (0.99 ** d) for d in range(n_days)]
        detail[f"DOWN{i}"] = _make_stock(closes)

    report = run_backtest(
        detail, horizon=1, top_frac=0.3, min_universe=10, weights={"momentum_20": 1.0}
    )
    assert report["sample_periods"] > 0
    # persistent trends mean past-momentum-implied long leg should keep winning
    assert report["mean_period_return"] > 0
    assert report["hit_rate"] > 0.5


def test_run_backtest_empty_detail_returns_no_samples():
    report = run_backtest({}, horizon=1)
    assert report["sample_periods"] == 0
    assert report["sharpe"] is None
    assert report["periods"] == []


def test_run_backtest_non_overlapping_periods_for_horizon():
    detail = {}
    n_days = 30
    for i in range(15):
        closes = [100 + d for d in range(n_days)]
        detail[f"A{i}"] = _make_stock(closes)
    for i in range(15):
        closes = [100 - d for d in range(n_days)]
        detail[f"B{i}"] = _make_stock(closes)

    report = run_backtest(detail, horizon=5, top_frac=0.3, min_universe=10)
    # non-overlapping: dates in consecutive periods should not overlap
    dates = [(p["date"], p["exit_date"]) for p in report["periods"]]
    for (d1, exit1), (d2, exit2) in zip(dates, dates[1:]):
        assert exit1 <= d2

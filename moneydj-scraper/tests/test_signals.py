from signals import (
    compute_factor_scores,
    institutional_flow,
    momentum,
    reversal_score,
    rsi,
    volume_ratio,
)


def _ohlc(closes, volumes=None):
    volumes = volumes or [1000] * len(closes)
    return [
        {"date": f"2026-01-{i+1:02d}", "close": c, "volume": v}
        for i, (c, v) in enumerate(zip(closes, volumes))
    ]


def test_momentum_basic():
    closes = [100, 101, 102, 103, 104, 105]
    assert momentum(_ohlc(closes), 5) == (105 - 100) / 100


def test_momentum_insufficient_data_returns_none():
    assert momentum(_ohlc([100, 101]), 5) is None


def test_momentum_zero_base_returns_none():
    closes = [0, 101, 102, 103, 104, 105]
    assert momentum(_ohlc(closes), 5) is None


def test_rsi_all_gains_is_100():
    closes = list(range(100, 116))  # strictly rising, 16 points -> period 14
    assert rsi(_ohlc(closes), period=14) == 100.0


def test_rsi_all_losses_is_0():
    closes = list(range(116, 100, -1))  # strictly falling
    assert rsi(_ohlc(closes), period=14) == 0.0


def test_rsi_insufficient_data_returns_none():
    assert rsi(_ohlc([100, 101, 102]), period=14) is None


def test_reversal_score_is_inverse_of_rsi():
    closes = list(range(100, 116))
    assert reversal_score(_ohlc(closes), period=14) == 50.0 - 100.0


def test_volume_ratio_breakout():
    closes = [100] * 21
    volumes = [1000] * 20 + [5000]
    assert volume_ratio(_ohlc(closes, volumes), lookback=20) == 5.0


def test_volume_ratio_insufficient_data_returns_none():
    assert volume_ratio(_ohlc([100, 101], [1000, 1000]), lookback=20) is None


def test_institutional_flow_sums_foreign_and_trust():
    institutional = [
        {"date": "2026-01-01", "foreign": 100, "trust": 50, "dealer": 10},
        {"date": "2026-01-02", "foreign": -30, "trust": 20, "dealer": -5},
    ]
    assert institutional_flow(institutional, lookback=2) == 100 + 50 - 30 + 20


def test_institutional_flow_empty_returns_none():
    assert institutional_flow([]) is None


def test_institutional_flow_all_none_values_returns_none():
    institutional = [{"date": "2026-01-01", "foreign": None, "trust": None}]
    assert institutional_flow(institutional) is None


def test_compute_factor_scores_shape():
    closes = list(range(100, 130))
    scores = compute_factor_scores(_ohlc(closes), [])
    assert set(scores.keys()) == {"momentum_20", "reversal", "volume_ratio", "institutional_flow"}
    assert scores["momentum_20"] is not None
    assert scores["institutional_flow"] is None

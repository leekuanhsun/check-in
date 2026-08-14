"""選股訊號（factor）計算：動能、均值回歸（RSI）、量能、三大法人籌碼流向。

全部是規則式計算的純函式，不做任何 I/O、不牽涉隨機性。權重（見 backtest.py 的
DEFAULT_WEIGHTS）是先驗給定的固定值，不是拿歷史資料反推出的最佳化參數——避免
「用同一份歷史資料調參數、再回頭用這份資料回測」這種樣本內過度配適。

跟 insights.py 的差異：insights.py 是給人看的文字摘要（純描述、不排序、不打分數）；
這裡是給 backtest.py／predict_stocks.py 用的數值訊號，用來做「哪些股票的訊號比較強」
的橫斷面排序。
"""
from typing import List, Optional


def momentum(ohlc: List[dict], lookback: int) -> Optional[float]:
    """N 日報酬率：close[-1] / close[-1-lookback] - 1。資料不足或除以零回傳 None。"""
    closes = [r["close"] for r in ohlc if r.get("close") is not None]
    if len(closes) < lookback + 1:
        return None
    old, new = closes[-1 - lookback], closes[-1]
    if not old:
        return None
    return (new - old) / old


def rsi(ohlc: List[dict], period: int = 14) -> Optional[float]:
    """N 期 RSI（簡單移動平均版，非 Wilder's smoothing），回傳 0-100。資料不足回傳 None。"""
    closes = [r["close"] for r in ohlc if r.get("close") is not None]
    if len(closes) < period + 1:
        return None
    window = closes[-(period + 1):]
    gains = [max(window[i] - window[i - 1], 0.0) for i in range(1, len(window))]
    losses = [max(window[i - 1] - window[i], 0.0) for i in range(1, len(window))]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def reversal_score(ohlc: List[dict], period: int = 14) -> Optional[float]:
    """均值回歸訊號：(50 - RSI)。RSI 越低（超賣）分數越高、預期越可能反彈；
    RSI 越高（超買）分數越低、預期越可能拉回。資料不足回傳 None。"""
    r = rsi(ohlc, period)
    return None if r is None else 50.0 - r


def volume_ratio(ohlc: List[dict], lookback: int = 20) -> Optional[float]:
    """今日成交量 / 過去 N 日（不含今日）均量。資料不足或均量為零回傳 None。"""
    volumes = [r["volume"] for r in ohlc if r.get("volume") is not None]
    if len(volumes) < lookback + 1:
        return None
    window = volumes[-(lookback + 1):-1]
    avg = sum(window) / len(window)
    if not avg:
        return None
    return volumes[-1] / avg


def institutional_flow(institutional: List[dict], lookback: int = 5) -> Optional[float]:
    """近 N 個交易日外資 + 投信合計買賣超（張）。完全沒有資料回傳 None。"""
    if not institutional:
        return None
    window = institutional[-lookback:] if lookback else institutional
    total = 0.0
    have_any = False
    for r in window:
        for key in ("foreign", "trust"):
            v = r.get(key)
            if v is not None:
                total += v
                have_any = True
    return total if have_any else None


def compute_factor_scores(ohlc: List[dict], institutional: List[dict]) -> dict:
    """算出單一股票在「目前這個時間點」的所有原始訊號值（未標準化）。

    傳入的 ohlc／institutional 必須已經是「只包含到某個時間點為止」的資料（呼叫端負責
    截斷，這裡不做日期過濾），才不會有 lookahead bias。任何個別訊號算不出來就是 None，
    由呼叫端（backtest.py 的橫斷面標準化）決定怎麼處理缺值。
    """
    return {
        "momentum_20": momentum(ohlc, 20),
        "reversal": reversal_score(ohlc),
        "volume_ratio": volume_ratio(ohlc),
        "institutional_flow": institutional_flow(institutional),
    }

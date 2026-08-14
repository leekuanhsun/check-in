"""Walk-forward 橫斷面因子回測引擎：多空十分位（long-short decile）投資組合。

方法論：
1. 對每個歷史交易日 t，只用「到 t 為止」的資料（不含 t 之後）算每檔股票的訊號分數
   （見 signals.py），避免 lookahead bias。
2. 每個訊號分別做橫斷面標準化（z-score，同一天所有股票互相比較），再依 DEFAULT_WEIGHTS
   加權平均成一個綜合分數。權重是先驗給定的固定值，不是拿這份回測資料反推最佳化出來的，
   所以這是「驗證一個固定規則的歷史表現」，不是「配適參數後拿同一份資料回頭測」的
   樣本內過度配適回測。
3. 依綜合分數排序，做多前 top_frac、放空後 top_frac（等權重），持有 horizon 個交易日，
   計算多空價差報酬（做多腳報酬 - 放空腳報酬）。
4. 用「不重疊」的區間往前滾動（每次跳 horizon 天，不是每天都滾動一次），避免同一段
   持有期間被算進好幾個「獨立」樣本裡、人為膨脹樣本數與低估報酬的自相關性。
5. 得到一串不重疊區間的多空組合報酬，再算年化 Sharpe（均值/標準差 * sqrt(252/horizon)）、
   累計報酬、勝率、最大回撤。

已知限制（務必如實呈現，不要包裝成穩健結果）：
- 目前歷史資料只有 ~58 個交易日（約 3 個月），日頻率下不重疊樣本數還有幾十筆，週頻率
  （horizon=5）只剩十筆左右——這是「初步驗證」等級，Sharpe 估計的標準誤差非常大，不是
  可以直接拿去下注的穩健結果。
- 放空腳在台股需要融券額度與成本，這裡假設可以無摩擦放空，實際報酬會比回測結果更低。
- 沒有計入交易成本／滑價／流動性限制，實際執行後報酬會打折扣。
- 月／季級別的回測需要遠比目前更長的歷史（至少 2-3 年），目前資料只夠做日／週級別。
"""
import math
from typing import Dict, List, Optional

from signals import compute_factor_scores

DEFAULT_WEIGHTS: Dict[str, float] = {
    "momentum_20": 1.0,
    "reversal": 1.0,
    "volume_ratio": 0.5,
    "institutional_flow": 1.0,
}

TRADING_DAYS_PER_YEAR = 252


def _date_index_map(rows: List[dict]) -> Dict[str, int]:
    return {r["date"]: i for i, r in enumerate(rows) if r.get("date")}


def _zscore_cross_section(raw: Dict[str, Optional[float]], min_count: int = 20) -> Dict[str, float]:
    """同一天、跨股票的橫斷面標準化。有效值太少（< min_count）就整個訊號當天跳過，
    不勉強用太小的樣本算平均數/標準差。"""
    values = [v for v in raw.values() if v is not None]
    if len(values) < min_count:
        return {}
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance)
    if std == 0:
        return {}
    return {sid: (v - mean) / std for sid, v in raw.items() if v is not None}


def composite_scores(
    factor_raw: Dict[str, Dict[str, Optional[float]]], weights: Dict[str, float]
) -> Dict[str, float]:
    """把多個訊號的橫斷面 z-score 依權重加權平均成單一綜合分數。

    個別股票缺某個訊號時，只用它有的訊號算加權平均（分母是「有值的訊號權重總和」），
    不會因為缺值就整檔股票排除，也不會讓缺值被當成 0 分拉低排名。
    """
    zscores = {factor: _zscore_cross_section(raw) for factor, raw in factor_raw.items()}
    stock_ids = set()
    for z in zscores.values():
        stock_ids.update(z.keys())

    composite: Dict[str, float] = {}
    for sid in stock_ids:
        weighted_sum = 0.0
        weight_total = 0.0
        for factor, weight in weights.items():
            z = zscores.get(factor, {})
            if sid in z:
                weighted_sum += weight * z[sid]
                weight_total += abs(weight)
        if weight_total > 0:
            composite[sid] = weighted_sum / weight_total
    return composite


def run_backtest(
    detail: Dict[str, dict],
    horizon: int = 1,
    top_frac: float = 0.1,
    weights: Optional[Dict[str, float]] = None,
    min_universe: int = 30,
) -> dict:
    """對 detail（universe_detail.json 的結構，{stock_id: {ohlc, institutional, ...}}）
    跑 walk-forward 多空十分位回測，回傳績效指標與逐區間報酬序列。

    horizon：持有期間（交易日數），1 = 隔日、5 ≈ 一週。用「不重疊」區間滾動（見模組
    docstring），所以樣本數是 (交易日數 / horizon) 量級，不是交易日數量級。
    top_frac：多空各取排序後前/後多少比例（0.1 = 前 10% 做多、後 10% 放空）。
    """
    weights = weights or DEFAULT_WEIGHTS

    ohlc_index: Dict[str, Dict[str, int]] = {}
    inst_index: Dict[str, Dict[str, int]] = {}
    for sid, d in detail.items():
        ohlc_index[sid] = _date_index_map(d.get("ohlc") or [])
        inst_index[sid] = _date_index_map(d.get("institutional") or [])

    # 用「擁有最完整歷史」的股票的日期序列當作交易日曆。
    calendar = max((sorted(idx.keys()) for idx in ohlc_index.values() if idx), key=len, default=[])

    period_returns: List[dict] = []

    for t in range(0, max(len(calendar) - horizon, 0), horizon):
        date_t = calendar[t]
        date_exit = calendar[t + horizon]

        factor_raw: Dict[str, Dict[str, Optional[float]]] = {
            "momentum_20": {}, "reversal": {}, "volume_ratio": {}, "institutional_flow": {},
        }
        entry_price: Dict[str, float] = {}
        exit_price: Dict[str, float] = {}

        for sid, d in detail.items():
            oi = ohlc_index[sid]
            if date_t not in oi or date_exit not in oi:
                continue
            ohlc_upto_t = d["ohlc"][: oi[date_t] + 1]
            ii = inst_index[sid]
            institutional_upto_t = d.get("institutional", [])[: ii[date_t] + 1] if date_t in ii else []

            scores = compute_factor_scores(ohlc_upto_t, institutional_upto_t)
            for factor in factor_raw:
                factor_raw[factor][sid] = scores.get(factor)

            entry_price[sid] = ohlc_upto_t[-1]["close"]
            exit_price[sid] = d["ohlc"][oi[date_exit]]["close"]

        composite = composite_scores(factor_raw, weights)
        if len(composite) < min_universe:
            continue

        ranked = sorted(composite.items(), key=lambda kv: kv[1], reverse=True)
        n = max(1, int(len(ranked) * top_frac))
        long_ids = [sid for sid, _ in ranked[:n]]
        short_ids = [sid for sid, _ in ranked[-n:]]

        def _leg_return(ids):
            rets = []
            for sid in ids:
                p0, p1 = entry_price.get(sid), exit_price.get(sid)
                if p0 and p1 is not None:
                    rets.append((p1 - p0) / p0)
            return sum(rets) / len(rets) if rets else None

        long_ret = _leg_return(long_ids)
        short_ret = _leg_return(short_ids)
        if long_ret is None or short_ret is None:
            continue

        period_returns.append(
            {
                "date": date_t,
                "exit_date": date_exit,
                "long_return": long_ret,
                "short_return": short_ret,
                "spread_return": long_ret - short_ret,
                "universe_size": len(composite),
            }
        )

    return _summarize(period_returns, horizon)


def _summarize(period_returns: List[dict], horizon: int) -> dict:
    if not period_returns:
        return {
            "horizon_days": horizon,
            "sample_periods": 0,
            "sharpe": None,
            "mean_period_return": None,
            "cumulative_return": None,
            "hit_rate": None,
            "max_drawdown": None,
            "periods": [],
        }

    spreads = [r["spread_return"] for r in period_returns]
    n = len(spreads)
    mean = sum(spreads) / n
    variance = sum((x - mean) ** 2 for x in spreads) / n if n > 1 else 0.0
    std = math.sqrt(variance)

    periods_per_year = TRADING_DAYS_PER_YEAR / horizon
    sharpe = (mean / std) * math.sqrt(periods_per_year) if std > 0 else None

    cumulative = 1.0
    for x in spreads:
        cumulative *= 1 + x
    cumulative_return = cumulative - 1

    hit_rate = sum(1 for x in spreads if x > 0) / n

    equity = [1.0]
    for x in spreads:
        equity.append(equity[-1] * (1 + x))
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak else 0.0
        max_dd = max(max_dd, dd)

    return {
        "horizon_days": horizon,
        "sample_periods": n,
        "sharpe": sharpe,
        "mean_period_return": mean,
        "cumulative_return": cumulative_return,
        "hit_rate": hit_rate,
        "max_drawdown": max_dd,
        "periods": period_returns,
    }

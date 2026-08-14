"""本益比（PE）估值：用同產業其他股票的本益比中位數，推算一檔股票的合理價位，
並打一個安全邊際折扣算出「建議買入價」。純函式，不做任何 I/O。

方法論（務必如實揭露，這是產業同儕比較估值，不是股價預測）：
1. EPS（每股盈餘）= 目前收盤價 / 本益比（PE = 股價 / EPS，反推）。
2. 產業平均本益比 = 同一個 category（TWSE 官方產業別分類，或 ETF/ETN 等商品類型）裡，
   其他股票本益比的「中位數」（比平均數更不受極端值影響），只採計本益比為正數的股票——
   虧損公司本益比多半是負值或無意義，不納入計算。同產業正值 PE 樣本數太少（< min_peers）
   就不產生該產業的估值基準，避免用兩三檔股票硬算出不可靠的「產業平均」。
3. 合理價位 = EPS x 產業平均本益比。
4. 建議買入價 = 合理價位 x 安全邊際（預設 0.9，即抓 10% 安全邊際，出自價值投資「用
   低於估值的價格買進、留緩衝空間」的保守傳統，不是精準預測）。

限制：
- 這是跟「同產業其他股票的本益比」比較，不是根據公司成長性、財務體質、獲利品質等
  基本面因素做的內在價值估算；本益比高低本身可能只是反映市場對成長性/風險的合理
  定價，不代表「本益比低就是便宜、該買」。
- TWSE 官方產業分類粗略，同產業內公司體質可能差異很大（例如同屬「其他電子業」的
  成熟公司跟成長股，合理本益比基準本來就不該一樣）。
- 本益比是單一時間點快照（BWIBBU_ALL 抓取當下），不是本益比河流圖那種長期歷史區間，
  無法判斷目前本益比在歷史相對高檔還是低檔。
- 不構成任何投資建議，僅供參考，投資有風險，請自行判斷。
"""
from typing import Dict, List, Optional


def compute_eps(close_price: Optional[float], pe_ratio: Optional[float]) -> Optional[float]:
    """EPS = 股價 / 本益比。本益比非正數（虧損公司常見）視為無法反推，回傳 None。"""
    if close_price is None or pe_ratio is None or pe_ratio <= 0:
        return None
    return close_price / pe_ratio


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def industry_median_pe(records: List[dict], min_peers: int = 3) -> Dict[str, float]:
    """依 category 分組，算出每個產業的本益比中位數（只採計正值 PE）。

    records 每筆需要有 "category" 與 "pe_ratio" 兩個鍵。同產業正值 PE 樣本數小於
    min_peers 就不產生該產業的估值基準（樣本太少不可靠，寧可缺值也不要硬湊）。
    """
    by_category: Dict[str, List[float]] = {}
    for r in records:
        category = r.get("category")
        pe = r.get("pe_ratio")
        if not category or pe is None or pe <= 0:
            continue
        by_category.setdefault(category, []).append(pe)

    result: Dict[str, float] = {}
    for category, pes in by_category.items():
        if len(pes) >= min_peers:
            median = _median(pes)
            if median is not None:
                result[category] = median
    return result


def recommended_buy_price(
    eps: Optional[float], industry_pe: Optional[float], margin_of_safety: float = 0.9
) -> Optional[float]:
    """建議買入價 = EPS x 產業平均本益比 x 安全邊際。任一輸入缺失或 EPS 非正回傳 None。"""
    if eps is None or industry_pe is None or eps <= 0:
        return None
    return eps * industry_pe * margin_of_safety


def valuation_gap_pct(close_price: Optional[float], recommended: Optional[float]) -> Optional[float]:
    """目前股價相對建議買入價的差距百分比：正值代表現價比建議買入價貴，負值代表比較便宜。"""
    if close_price is None or recommended is None or recommended <= 0:
        return None
    return (close_price - recommended) / recommended * 100

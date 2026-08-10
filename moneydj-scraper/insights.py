"""依歷史數據整理重點觀點：純粹統計/事實陳述，不做任何預測或投資建議。

規則：近 5 / 20 個交易日股價漲跌幅、收盤價相對 5 日均價位置、三大法人（外資/投信）
近期累計買賣超、融資融券餘額變化。任一區塊資料不足就略過該條，不硬湊。
"""
from typing import List, Optional


def _pct_change(old: Optional[float], new: Optional[float]) -> Optional[float]:
    if old in (None, 0) or new is None:
        return None
    return (new - old) / old * 100


def summarize_stock_insights(
    ohlc: List[dict], institutional: List[dict], margin: List[dict]
) -> List[str]:
    bullets: List[str] = []

    closes = [r["close"] for r in ohlc if r.get("close") is not None] if ohlc else []
    if closes:
        latest = closes[-1]
        if len(closes) >= 6:
            chg5 = _pct_change(closes[-6], latest)
            if chg5 is not None:
                direction = "上漲" if chg5 >= 0 else "下跌"
                bullets.append(f"近 5 個交易日股價{direction} {abs(chg5):.2f}%")
        if len(closes) >= 21:
            chg20 = _pct_change(closes[-21], latest)
            if chg20 is not None:
                direction = "上漲" if chg20 >= 0 else "下跌"
                bullets.append(f"近 20 個交易日股價{direction} {abs(chg20):.2f}%")
        window = closes[-5:] if len(closes) >= 5 else closes
        ma5 = sum(window) / len(window)
        position = "之上" if latest >= ma5 else "之下"
        bullets.append(f"收盤價位於 5 日均價（{ma5:.2f}）{position}")

    if institutional:
        n = len(institutional)
        foreign_values = [r.get("foreign") for r in institutional if r.get("foreign") is not None]
        trust_values = [r.get("trust") for r in institutional if r.get("trust") is not None]
        if foreign_values:
            foreign_sum = sum(foreign_values)
            f_dir = "買超" if foreign_sum >= 0 else "賣超"
            bullets.append(f"外資近 {n} 個交易日累計{f_dir} {abs(foreign_sum):,} 張")
        if trust_values:
            trust_sum = sum(trust_values)
            t_dir = "買超" if trust_sum >= 0 else "賣超"
            bullets.append(f"投信近 {n} 個交易日累計{t_dir} {abs(trust_sum):,} 張")

    if len(margin) >= 2:
        n = len(margin)
        first, last = margin[0], margin[-1]
        if first.get("margin_balance") is not None and last.get("margin_balance") is not None:
            diff = last["margin_balance"] - first["margin_balance"]
            direction = "增加" if diff >= 0 else "減少"
            bullets.append(f"融資餘額較 {n} 個交易日前{direction} {abs(diff):,} 張")
        if first.get("short_balance") is not None and last.get("short_balance") is not None:
            diff = last["short_balance"] - first["short_balance"]
            direction = "增加" if diff >= 0 else "減少"
            bullets.append(f"融券餘額較 {n} 個交易日前{direction} {abs(diff):,} 張")

    if bullets:
        bullets.append("以上僅為歷史數據統計整理，不構成任何投資建議，亦不代表對未來股價的預測。")
    return bullets

"""產生「預測上漲排行」＋誠實回測報告，寫到 predictions.json。

跟 insights.py／dashboard 現有的「當日漲跌幅排行」不同：那是純粹描述過去已發生的事實
（今天漲最多的是誰），這裡是用 signals.py 的規則式訊號（動能／均值回歸／量能／三大法人
籌碼流向）算出的綜合分數，對「未來」報酬方向做排序——這是這個專案第一個具有預測性質
的功能，務必附上如實的回測結果與限制說明，不能只給排行榜、不給驗證過的績效。

目前只做日／週兩個持有期間：現有歷史（~58 個交易日）不夠支撐月／季級別有意義的回測
（月/季至少需要 2-3 年歷史），硬做只會產生看似穩健、實則樣本數個位數的假象。
"""
import json
from datetime import datetime, timezone
from typing import Dict, List

from backtest import DEFAULT_WEIGHTS, composite_scores, run_backtest
from signals import compute_factor_scores

HORIZONS = {"daily": 1, "weekly": 5}
TOP_N = 20
SINGLE_FACTORS = ["momentum_20", "reversal", "volume_ratio", "institutional_flow"]

DISCLAIMER = (
    "本排行是用歷史價量與三大法人籌碼資料，依固定規則（非用回測資料反推最佳化）算出的"
    "綜合分數排序，並附上樣本外可信度有限的歷史回測績效（見 backtest_report）。"
    "目前歷史資料僅約 58 個交易日，樣本數很小，Sharpe 估計標準誤差大；未計入交易成本、"
    "滑價、融券可行性與額度限制。這是統計方法的初步驗證結果，不是投資建議，不保證未來"
    "表現，投資有風險，請自行判斷並承擔全部風險。"
)


def _load_detail(path: str = "universe_detail.json") -> Dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _current_rankings(detail: Dict[str, dict], top_n: int = TOP_N) -> List[dict]:
    """用「目前為止的全部資料」（不截斷）算每檔股票現在的綜合分數，回傳排名前 top_n 檔。"""
    factor_raw: Dict[str, Dict[str, float]] = {
        "momentum_20": {}, "reversal": {}, "volume_ratio": {}, "institutional_flow": {},
    }
    for sid, d in detail.items():
        scores = compute_factor_scores(d.get("ohlc") or [], d.get("institutional") or [])
        for factor in factor_raw:
            factor_raw[factor][sid] = scores.get(factor)

    composite = composite_scores(factor_raw, DEFAULT_WEIGHTS)
    ranked = sorted(composite.items(), key=lambda kv: kv[1], reverse=True)[:top_n]

    rankings = []
    for sid, score in ranked:
        d = detail[sid]
        ohlc = d.get("ohlc") or []
        rankings.append(
            {
                "stock_id": sid,
                "composite_score": round(score, 4),
                "close_price": ohlc[-1]["close"] if ohlc else None,
                "factors": {k: factor_raw[k].get(sid) for k in factor_raw},
            }
        )
    return rankings


def main() -> None:
    print("loading universe_detail.json...")
    detail = _load_detail()
    print(f"loaded {len(detail)} stocks")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "weights": DEFAULT_WEIGHTS,
        "disclaimer": DISCLAIMER,
        "horizons": {},
    }

    for label, horizon_days in HORIZONS.items():
        print(f"running walk-forward backtest for horizon={label} ({horizon_days} 交易日)...")
        report = run_backtest(detail, horizon=horizon_days)
        sharpe_str = f"{report['sharpe']:.2f}" if report["sharpe"] is not None else "N/A"
        print(
            f"  {label}: sample_periods={report['sample_periods']}, sharpe={sharpe_str}, "
            f"hit_rate={report['hit_rate']}, cumulative_return={report['cumulative_return']}"
        )
        single_factor_reports = {}
        for factor in SINGLE_FACTORS:
            fr = run_backtest(detail, horizon=horizon_days, weights={factor: 1.0})
            single_factor_reports[factor] = {
                "sample_periods": fr["sample_periods"],
                "sharpe": fr["sharpe"],
                "hit_rate": fr["hit_rate"],
                "cumulative_return": fr["cumulative_return"],
            }

        output["horizons"][label] = {
            "horizon_days": horizon_days,
            "backtest_report": report,
            "single_factor_breakdown": single_factor_reports,
        }

    print("computing current rankings...")
    rankings = _current_rankings(detail)
    output["current_top_rankings"] = rankings
    output["monthly_quarterly_status"] = (
        "尚未提供：月/季級別的回測需要至少 2-3 年歷史資料，目前僅有約 58 個交易日"
        "（fetch_universe_detail.py 的預設抓取範圍），統計上不足以驗證月/季訊號的有效性。"
    )

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"wrote predictions.json: top {len(rankings)} rankings, 2 backtest horizons")


if __name__ == "__main__":
    main()

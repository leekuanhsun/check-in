"""合併 universe_stocks.json（收盤價／產業分類）與 universe_detail.json（本益比等基本
資訊），依 valuation.py 的產業同儕比較法算出每檔股票的建議買入價，輸出 valuations.json。

跟 fetch_*.py 系列不同：這支不打任何網路請求，純粹是本地端對既有兩份真實資料做
二次加工計算，執行速度是毫秒級。
"""
import json

from valuation import compute_eps, industry_median_pe, recommended_buy_price, valuation_gap_pct


def _to_float(text):
    if text is None:
        return None
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return None


def main() -> None:
    with open("universe_stocks.json", encoding="utf-8") as f:
        stocks = json.load(f)
    with open("universe_detail.json", encoding="utf-8") as f:
        detail = json.load(f)

    records = []
    for s in stocks:
        stock_id = s["stock_id"]
        fundamentals = (detail.get(stock_id) or {}).get("fundamentals") or {}
        records.append(
            {
                "stock_id": stock_id,
                "stock_name": s.get("stock_name"),
                "category": s.get("category"),
                "close_price": _to_float(s.get("close_price")),
                "pe_ratio": fundamentals.get("pe_ratio"),
            }
        )

    industry_pe = industry_median_pe(records)

    results = {}
    for r in records:
        eps = compute_eps(r["close_price"], r["pe_ratio"])
        ind_pe = industry_pe.get(r["category"])
        rec_price = recommended_buy_price(eps, ind_pe)
        gap = valuation_gap_pct(r["close_price"], rec_price)
        results[r["stock_id"]] = {
            "eps": round(eps, 2) if eps is not None else None,
            "industry_median_pe": round(ind_pe, 2) if ind_pe is not None else None,
            "recommended_buy_price": round(rec_price, 2) if rec_price is not None else None,
            "valuation_gap_pct": round(gap, 2) if gap is not None else None,
        }

    with open("valuations.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    got = sum(1 for r in results.values() if r["recommended_buy_price"] is not None)
    print(f"wrote valuations.json: {len(results)} stocks, {got} with recommended buy price")


if __name__ == "__main__":
    main()

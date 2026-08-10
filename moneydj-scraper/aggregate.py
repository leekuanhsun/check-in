"""跨來源彙整：同一檔股票如果在多個網站都被列為同一家公司的概念股，可信度較高。"""
from typing import Dict, List, Optional
from urllib.parse import urlparse

from models import StockRecord


def _site_of(url: Optional[str]) -> str:
    if not url:
        return "unknown"
    netloc = urlparse(url).netloc
    return netloc or "unknown"


def summarize_by_stock(records: List[StockRecord]) -> List[dict]:
    """依 stock_id 分組，回傳每檔股票被幾個不同網站列為概念股、分類與最新一筆價格。

    結果依「來源網站數量」由多到少排序：出現在越多網站的股票，通常代表市場上
    對它是該供應鏈一員的共識越高（僅供參考，不代表真實供應關係已被驗證）。
    """
    groups: Dict[str, dict] = {}
    for r in records:
        if not r.stock_id:
            continue
        group = groups.setdefault(
            r.stock_id,
            {
                "stock_id": r.stock_id,
                "stock_name": r.stock_name,
                "categories": set(),
                "sites": set(),
                "latest_close_price": None,
                "latest_change_pct": None,
            },
        )
        if r.category:
            group["categories"].add(r.category)
        group["sites"].add(_site_of(r.source_url))
        if r.close_price:
            group["latest_close_price"] = r.close_price
        if r.change_pct:
            group["latest_change_pct"] = r.change_pct

    summaries = []
    for group in groups.values():
        summaries.append(
            {
                "stock_id": group["stock_id"],
                "stock_name": group["stock_name"],
                "categories": sorted(group["categories"]),
                "sites": sorted(group["sites"]),
                "source_count": len(group["sites"]),
                "latest_close_price": group["latest_close_price"],
                "latest_change_pct": group["latest_change_pct"],
            }
        )
    summaries.sort(key=lambda s: (-s["source_count"], s["stock_id"]))
    return summaries

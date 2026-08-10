"""美股公司 → 台灣供應鏈概念股頁面對照表。

不綁定單一資料來源：每家美股公司底下可以同時列多個台灣財經網站（MoneyDJ、
鉅亨網、玩股網、Goodinfo……任何網站皆可）的概念股頁面網址，格式與既有的
`targets.json` 相容（url / category），`scraper.run_batch` 可直接吃這份清單。

目前這類頁面幾乎沒有網站會提供穩定、公開的「用美股公司名稱搜尋」API，所以
採「人工維護對照表」而非自動搜尋：準確度較高、也不會因為猜測搜尋網址格式
而爬到錯誤頁面。參考格式見 `company_map.example.json`。
"""
import json
from typing import Dict, List, Optional


def load_company_map(path: str) -> Dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_company_targets(
    company_map: Dict[str, dict], query: str
) -> Optional[List[Dict[str, str]]]:
    """依公司名稱或別名（不分大小寫）找出對照表中的 targets 清單；找不到回傳 None。"""
    query_lower = query.strip().lower()
    for company, info in company_map.items():
        names = [company] + list(info.get("aliases", []))
        if any(query_lower == n.strip().lower() for n in names):
            return info.get("targets", [])
    return None


def list_companies(company_map: Dict[str, dict]) -> List[str]:
    return sorted(company_map.keys())

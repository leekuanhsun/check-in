"""資料模型層：StockRecord。"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StockRecord:
    stock_id: Optional[str]
    stock_name: Optional[str]
    role: Optional[str] = None
    close_price: Optional[str] = None
    change: Optional[str] = None
    change_pct: Optional[str] = None
    volume: Optional[str] = None
    category: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def change_pct_float(self) -> Optional[float]:
        if not self.change_pct:
            return None
        try:
            return float(self.change_pct.replace("%", "").replace(",", "").strip())
        except ValueError:
            return None

"""產生範例輸出資料，供 dashboard 展示用（非真實即時報價）。

因目前執行環境的出網政策擋掉 moneydj.com，暫時無法對真實頁面跑爬蟲，
故用本腳本產生格式與 StockRecord 完全一致的範例資料，方便先行驗證/展示
儀表板；待日後在可連外的環境執行 main.py 取得真實資料後，可直接用
dashboard 的「上傳 JSON」功能載入取代。
"""
import json
import random
from dataclasses import asdict
from datetime import datetime

from models import StockRecord

random.seed(20260809)

CATEGORIES = {
    "AI 伺服器供應鏈": [
        ("2330", "台積電", "晶圓代工"),
        ("2317", "鴻海", "系統組裝"),
        ("2382", "廣達", "伺服器組裝"),
        ("3231", "緯創", "伺服器組裝"),
        ("2356", "英業達", "伺服器組裝"),
        ("6669", "緯穎", "雲端伺服器"),
        ("2308", "台達電", "電源供應器"),
    ],
    "電動車供應鏈": [
        ("1519", "華城", "電力設備"),
        ("6213", "聯茂", "PCB 材料"),
        ("2360", "致茂", "測試設備"),
        ("1503", "士電", "重電設備"),
        ("3037", "欣興", "PCB"),
        ("8155", "訊芯-KY", "被動元件"),
    ],
    "半導體封測": [
        ("3711", "日月光投控", "封測大廠"),
        ("6239", "力成", "記憶體封測"),
        ("2449", "京元電子", "IC 測試"),
        ("6147", "頎邦", "驅動 IC 封測"),
        ("3374", "精材", "晶圓級封裝"),
    ],
}

records = []
for category, stocks in CATEGORIES.items():
    for stock_id, stock_name, role in stocks:
        close = round(random.uniform(35, 980), 2)
        pct = round(random.uniform(-6.5, 6.5), 2)
        change = round(close * pct / 100, 2)
        volume = random.randint(800, 45000)
        records.append(
            StockRecord(
                stock_id=stock_id,
                stock_name=stock_name,
                role=role,
                close_price=f"{close:.2f}",
                change=f"{change:+.2f}",
                change_pct=f"{pct:+.2f}%",
                volume=f"{volume:,}",
                category=category,
                source_url="https://www.moneydj.com/z/zc/zca/zca_0.djhtm",
                scraped_at=datetime(2026, 8, 9, 13, 30, 0).isoformat(timespec="seconds"),
            )
        )

with open("sample_output.json", "w", encoding="utf-8") as f:
    json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)

print(f"wrote {len(records)} sample records to sample_output.json")

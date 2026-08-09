"""共用 logging 設定：寫入 moneydj_scraper.log 並輸出至 stdout。"""
import logging
import sys
from pathlib import Path

LOG_PATH = Path(__file__).with_name("moneydj_scraper.log")

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    _configured = True


setup_logging()

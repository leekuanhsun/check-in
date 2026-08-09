"""請求層：HTTP 抓取、UA 輪替、編碼偵測、重試。"""
import logging
import random
import time
from typing import Optional

import requests

from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",
]

# MoneyDJ 頁面以 Big5 編碼為主，依序嘗試解碼
ENCODING_CANDIDATES = ["big5", "cp950", "utf-8"]


def _decode(content: bytes) -> str:
    for encoding in ENCODING_CANDIDATES:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def fetch_html(
    url: str,
    timeout: int = 10,
    retries: int = 3,
    backoff_base: float = 1.0,
) -> Optional[str]:
    """抓取頁面 HTML；失敗（含逾時、HTTP 錯誤）以指數退避重試，最終仍失敗回傳 None。"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.moneydj.com/",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return _decode(resp.content)
        except requests.exceptions.RequestException as exc:
            logger.warning("fetch attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt == retries:
                logger.error("fetch failed for %s after %d attempts", url, retries)
                return None
            time.sleep(backoff_base * (2 ** (attempt - 1)))
    return None

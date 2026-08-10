# 供應鏈概念股爬蟲

爬取台灣財經網站上的概念股/供應鏈頁面，擷取股票代碼、名稱、當日價格與漲跌幅，輸出結構化 JSON。
**不限定單一資料來源**：同一家美股公司（如輝達、蘋果）底下可以同時掛 MoneyDJ、鉅亨網、玩股網、
Goodinfo 等任何網站的頁面，爬完後再跨來源比對。不做股價預測，僅提供資料擷取、當日漲跌幅排序、
以及「同一檔股票在幾個網站都被列為概念股」的信心度彙整。

## 模組結構

```
fetcher.py             請求層：UA 輪替、Big5/cp950/utf-8 解碼、重試（指數退避）
parser.py               解析層：表格解析、欄位映射、_split_id_and_name / _extract_id_from_href、rank_today_gainers
models.py               資料模型：StockRecord
company_map.py          美股公司 → 多來源概念股頁面對照表（不綁定單一網站）
aggregate.py            跨來源彙整：同一檔股票出現在幾個網站
tradingview.py          （選用）報價層：用 TradingView 批次查價，取代/覆蓋頁面本身的價格欄位
scraper.py               批次控制 + 輸出層：MoneyDJConceptScraper（run_batch / run_batch_with_tradingview_quotes / save_json / inspect_page）
main.py                  CLI 入口
tests/                   pytest 單元測試
```

`scraper.py`/`parser.py` 的解析邏輯（找最大 `<table>` + 依 `%` 儲存格定位欄位）本身沒有寫死
MoneyDJ 專屬的東西，理論上適用大部分「股票代碼/名稱/收盤/漲跌/漲跌%/成交量」欄位齊全的
中文財經網站表格；但每個網站實際 HTML 結構不同，正式串接新網站前務必先用 `--inspect` 核對。

## 安裝

```bash
pip install -r requirements.txt        # 執行期依賴
pip install -r requirements-dev.txt    # 加上 pytest（開發/測試用）
```

## 使用方式

### 1. 單一 targets 清單（原本用法）

先用 `--inspect` 核對目標頁面的表格結構：

```bash
python main.py --inspect "https://www.moneydj.com/z/zc/zca/zca_0.djhtm"
```

依印出的表格 HTML，調整 `parser.py` 中 `_parse_row` 的欄位索引邏輯。接著準備目標清單（參考
`targets.example.json`），url 可以是任何網站，不限 MoneyDJ：

```json
[
  {"url": "https://www.moneydj.com/...", "category": "半導體供應鏈"},
  {"url": "https://www.cnyes.com/...", "category": "半導體供應鏈（鉅亨網）"}
]
```

```bash
python main.py --targets targets.json --output moneydj_concept_stocks.json --top 10
```

### 2. 用美股公司名稱查多來源對照表

先依 `company_map.example.json` 的格式建立自己的對照表（每家美股公司底下列多個網站的頁面
網址），再用 `--company` + `--company-map` 取代 `--targets`：

```bash
python main.py --company "輝達" --company-map company_map.json \
  --output nvidia_concept_stocks.json \
  --summary-output nvidia_summary.json
```

`--company` 可用公司名稱或對照表裡的別名（大小寫不拘）。`--summary-output` 會額外輸出
`aggregate.summarize_by_stock` 的彙整結果：每檔股票出現在幾個不同網域、屬於哪些分類、
最新一筆價格——`source_count` 越高，代表越多網站的編輯都把它列為該公司概念股。

目前沒有任何網站提供穩定、公開的「用美股公司名稱搜尋概念股頁面」API，所以 `company_map.json`
採人工維護：準確度較高，也不會因為亂猜搜尋網址格式而爬到錯誤頁面。

### 報價來源：頁面本身 或 TradingView

預設（`--quotes-source moneydj`）價格欄位直接來自目標頁面本身。

若想改成「頁面只取分類/成分股，報價改用 TradingView 覆蓋」，加上 `--quotes-source tradingview`：

```bash
python main.py --targets targets.json --quotes-source tradingview
```

流程：`run_batch` 先取得每個分類底下的股票代碼/名稱/角色 → 對每個代碼呼叫
`tradingview.resolve_symbol` 解析成 `TWSE:2330` / `TPEX:xxxx` 格式 → `tradingview.fetch_quotes`
批次向 TradingView 查價 → `tradingview.apply_quote` 覆蓋 `close_price` / `change` / `change_pct` /
`volume`。查無報價的股票會保留原頁面解析出的數值（若有）作為備援，不會整筆丟棄。

**重要注意事項**：`tradingview.py` 用的是 TradingView 網頁版篩選器（screener）內部在用的端點
（`symbol-search.tradingview.com`、`scanner.tradingview.com`），**未公開、非官方文件化**，格式可能
隨時變動。正式使用前務必：

1. 用 `tradingview.debug_fetch_raw(symbols)` 印出原始回應，核對欄位名稱是否還是
   `QUOTE_FIELDS = ["close", "change", "change_abs", "volume"]` 這組，不吻合要自行調整。
2. 自行確認 TradingView 使用條款，避免高頻或大量請求（`resolve_symbols` 內建了逐筆延遲）。
3. 這個環境目前無法連線到外部網站實測（見「已知限制」），程式碼與單元測試都以純函式
   （`apply_quote`）驗證合併邏輯，實際串接後請先小量測試再擴大 targets。

## 測試

```bash
pytest
```

單元測試涵蓋純函式（`_split_id_and_name`、`_extract_id_from_href`、`StockRecord.change_pct_float`、
`rank_today_gainers`、`tradingview.apply_quote`、`company_map.resolve_company_targets`、
`aggregate.summarize_by_stock`）與 `parse_page` 對假 HTML 表格的解析。

## 已知限制

- `role`（細分產業角色）欄位多數頁面沒有獨立欄位，需依實際頁面結構在 `_parse_row` 內補上對應邏輯。
- 不同網站/頁面的欄位順序可能不同，請先跑 `--inspect` 核對後再調整；`parser.py` 目前的通用表格
  啟發式（找最大 table + `%` 儲存格定位）不保證適用所有網站。
- `company_map.json` 需要人工維護每家公司的目標頁面網址，沒有自動搜尋機制。
- 反爬蟲方面目前有 User-Agent 輪替、隨機延遲、以及抓取失敗時的指數退避重試（`fetch_html` 的
  `retries`/`backoff_base` 參數）；若對方有更嚴格的頻率限制或需要 Cookie/Session 驗證，需自行加上
  `requests.Session()` 的 cookie 持久化、或改用瀏覽器自動化工具。
- 不含任何股價預測邏輯，`rank_today_gainers`／`aggregate.summarize_by_stock` 都只是資料排序/計數，
  「多來源都列為概念股」不代表真實供應關係已被驗證，僅供參考。
- **開發此專案的環境本身出網政策擋掉了一般外部網站**（moneydj.com、tradingview.com、
  cnyes.com 等皆連不到，代理回傳 403），所以爬取邏輯未曾對真實頁面驗證過，`_parse_row` 的欄位
  索引、`tradingview.py` 的端點/欄位名稱、`company_map.example.json` 裡的網址都是佔位/未驗證，
  需要你在有網路的環境先小量測試、核對後再正式使用。

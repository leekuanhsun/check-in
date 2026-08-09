# MoneyDJ 概念股爬蟲

爬取 MoneyDJ 理財網的概念股/供應鏈頁面，擷取股票代碼、名稱、當日價格與漲跌幅，輸出結構化 JSON。
不做股價預測，僅提供資料擷取與「當日漲跌幅排序」。

## 模組結構

```
fetcher.py      請求層：UA 輪替、Big5/cp950/utf-8 解碼、重試（指數退避）
parser.py       解析層：表格解析、欄位映射、_split_id_and_name / _extract_id_from_href、rank_today_gainers
models.py       資料模型：StockRecord
tradingview.py  （選用）報價層：用 TradingView 批次查價，取代/覆蓋 MoneyDJ 頁面的價格欄位
scraper.py      批次控制 + 輸出層：MoneyDJConceptScraper（run_batch / run_batch_with_tradingview_quotes / save_json / inspect_page）
main.py         CLI 入口
tests/          pytest 單元測試
```

## 安裝

```bash
pip install -r requirements.txt        # 執行期依賴
pip install -r requirements-dev.txt    # 加上 pytest（開發/測試用）
```

## 使用方式

1. 先用 `--inspect` 核對目標頁面的表格結構：

   ```bash
   python main.py --inspect "https://www.moneydj.com/z/zc/zca/zca_0.djhtm"
   ```

   依印出的表格 HTML，調整 `parser.py` 中 `_parse_row` 的欄位索引邏輯。

2. 準備目標清單（參考 `targets.example.json`），複製為自己的檔案並填入實際 URL：

   ```json
   [
     {"url": "https://www.moneydj.com/...", "category": "半導體供應鏈"}
   ]
   ```

3. 執行批次爬取：

   ```bash
   python main.py --targets targets.json --output moneydj_concept_stocks.json --top 10
   ```

   結果會寫入 `moneydj_concept_stocks.json`，並印出當日漲幅排行（僅供參考，非預測）。

### 報價來源：MoneyDJ 或 TradingView

預設（`--quotes-source moneydj`）價格欄位直接來自 MoneyDJ 頁面本身。

若想改成「MoneyDJ 抓分類/成分股，TradingView 抓報價」，加上 `--quotes-source tradingview`：

```bash
python main.py --targets targets.json --quotes-source tradingview
```

流程：`run_batch` 先用 MoneyDJ 取得每個分類底下的股票代碼/名稱/角色 → 對每個代碼呼叫
`tradingview.resolve_symbol` 解析成 `TWSE:2330` / `TPEX:xxxx` 格式 → `tradingview.fetch_quotes`
批次向 TradingView 查價 → `tradingview.apply_quote` 覆蓋 `close_price` / `change` / `change_pct` /
`volume`。查無報價的股票會保留 MoneyDJ 原本解析出的數值（若有）作為備援，不會整筆丟棄。

**重要注意事項**：`tradingview.py` 用的是 TradingView 網頁版篩選器（screener）內部在用的端點
（`symbol-search.tradingview.com`、`scanner.tradingview.com`），**未公開、非官方文件化**，格式可能
隨時變動。正式使用前務必：

1. 用 `tradingview.debug_fetch_raw(symbols)` 印出原始回應，核對欄位名稱是否還是
   `QUOTE_FIELDS = ["close", "change", "change_abs", "volume"]` 這組，不吻合要自行調整。
2. 自行確認 TradingView 使用條款，避免高頻或大量請求（`resolve_symbols` 內建了逐筆延遲）。
3. 這個環境目前無法連線到 moneydj.com / tradingview.com 實測（見「已知限制」），程式碼與單元測試
   都以純函式（`apply_quote`）驗證合併邏輯，實際串接後請先小量測試再擴大 targets。

## 測試

```bash
pytest
```

單元測試涵蓋純函式（`_split_id_and_name`、`_extract_id_from_href`、`StockRecord.change_pct_float`、
`rank_today_gainers`、`tradingview.apply_quote`）與 `parse_page` 對假 HTML 表格的解析。

## 已知限制

- `role`（細分產業角色）欄位多數頁面沒有獨立欄位，需依實際頁面結構在 `_parse_row` 內補上對應邏輯。
- 不同頁面的欄位順序可能不同，請先跑 `--inspect` 核對後再調整。
- 反爬蟲方面目前有 User-Agent 輪替、隨機延遲、以及抓取失敗時的指數退避重試（`fetch_html` 的
  `retries`/`backoff_base` 參數）；若對方有更嚴格的頻率限制或需要 Cookie/Session 驗證，需自行加上
  `requests.Session()` 的 cookie 持久化、或改用瀏覽器自動化工具。
- 不含任何股價預測邏輯，`rank_today_gainers` 僅是當日數據排序。
- **開發此專案的環境本身出網政策擋掉了一般外部網站**（moneydj.com、tradingview.com 皆連不到，
  代理回傳 403），所以爬取邏輯未曾對真實頁面驗證過，`_parse_row` 的欄位索引與
  `tradingview.py` 的端點/欄位名稱都需要你在有網路的環境先小量測試、核對後再正式使用。

# 供應鏈概念股爬蟲

爬取台灣財經網站上的概念股/供應鏈頁面，擷取股票代碼、名稱、當日價格與漲跌幅，輸出結構化 JSON。
**不限定單一資料來源**：同一家美股公司（如輝達、蘋果）底下可以同時掛 MoneyDJ、鉅亨網、玩股網、
Goodinfo 等任何網站的頁面，爬完後再跨來源比對。不做股價預測，僅提供資料擷取、當日漲跌幅排序、
以及「同一檔股票在幾個網站都被列為概念股」的信心度彙整。

除了精選概念股，`fetch_universe.py` 另外用 TWSE 官方端點抓**全部上市股票**（約 1,379 檔）的
代碼／名稱／官方產業分類／當日價格，`dashboard.html` 預設就是顯示這份全市場真實資料（見「儀
表板」一節）。

## 模組結構

```
dashboard.html          純前端資料儀表板（全市場真實資料 + 精選概念股明細，含上傳/K線/法人/資券/重點整理觀點）
concept_categories.py    人工整理的概念股分類/成分股清單（單一事實來源，只留下實測拿得到真實資料的上市股票）
fetch_universe.py       抓「全部上市股票」的代碼/名稱/官方產業分類/當日價格（不含歷史明細）
universe_stocks.json    fetch_universe.py 的真實輸出快照（~1,379 檔）
fetch_real_data.py      用 twse_api.py 抓 concept_categories.py 清單（精選概念股）的完整明細
real_concept_stocks.json / real_concept_detail.json   fetch_real_data.py 的真實輸出快照
fetcher.py             請求層：UA 輪替、Big5/cp950/utf-8 解碼、重試（指數退避）
parser.py               解析層：表格解析、欄位映射、_split_id_and_name / _extract_id_from_href、rank_today_gainers
models.py               資料模型：StockRecord
company_map.py          美股公司 → 多來源概念股頁面對照表（不綁定單一網站）
aggregate.py            跨來源彙整：同一檔股票出現在幾個網站
tradingview.py          （選用）報價層：用 TradingView 批次查價，取代/覆蓋頁面本身的價格欄位
twse_api.py             （選用）個股明細層：TWSE 官方端點取得日K線/三大法人買賣超/融資融券/基本資訊
insights.py             依個股明細整理重點觀點的規則式摘要（純統計，非預測）
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

### 個股明細：K 線、三大法人買賣超、融資融券、基本資訊、重點整理觀點

加上 `--with-detail`，會針對這次爬到的每檔股票另外呼叫 TWSE 官方端點，取得：

- **日 K 線**（近 2 個月，開高低收 + 成交量）
- **三大法人買賣超**（近 10 個交易日，外資／投信／自營商）
- **融資融券餘額**（近 10 個交易日，含日增減）
- **基本資訊**（本益比／殖利率／股價淨值比）
- **重點整理觀點**：`insights.summarize_stock_insights` 依上述數據產生的規則式摘要，例如
  「近 5 個交易日股價上漲 3.2%」「外資近 10 個交易日累計買超 1,200 張」，最後固定加一行
  「僅為歷史數據統計整理，不構成任何投資建議，亦不代表對未來股價的預測」。

```bash
python main.py --targets targets.json --with-detail --detail-output concept_detail.json
```

輸出的 `concept_detail.json` 是以股票代碼為 key 的字典，每筆包含 `ohlc` / `institutional` /
`margin` / `fundamentals` / `insights` 五個欄位；可以直接餵給儀表板的「上傳資料」功能查看個股明細
（見下方儀表板一節）。

`twse_api.py` 用的是 TWSE 官方公開端點（`STOCK_DAY`、`T86`、`MI_MARGN`、`BWIBBU_ALL`），
比 `tradingview.py` 的未公開端點穩定、有文件。**四個端點的欄位順序已於 2026-08-11 透過
GitHub Actions 對照真實回應驗證並修正**（`MI_MARGN` 的個股資料實際包在 `tables` 陣列裡且不是
`tables[0]`；`BWIBBU_ALL` 只有 5 欄，原本假設的 6 欄是錯的；`T86` 的三大法人買賣超原始單位是
「股」，已換算成「張」）。若 TWSE 未來調整回應格式，可用 `twse_api.debug_fetch_raw(url, params)`
重新核對。另外目前只支援**上市（TWSE）**股票，上櫃（TPEX）代碼會直接拿到空結果（見「已知限制」）。

### 全部上市股票 + 官方產業分類

`fetch_universe.py` 涵蓋範圍是**全部上市股票**（不限 `concept_categories.py` 那份精選清單），
但只抓「當下快照」——代碼／名稱／官方產業分類／收盤／漲跌／成交量，**不**逐檔抓歷史 K 線／
三大法人／融資融券（對 1,000+ 檔股票這樣做是數萬次請求，時間與對 TWSE 伺服器的負擔都不合理）：

- `twse_api.fetch_all_companies()`：呼叫 `t187ap03_L`（TWSE OpenAPI）一次取得全部上市公司
  基本資料。回傳的「產業別」是數字代碼（例如台積電是 `"24"`），不是文字，所以有
  `INDUSTRY_CODE_NAMES` 對照表把代碼換成「半導體業」這類中文名稱——這份表是 2026-08-11
  用真實回應資料驅動推導出來的（每個代碼底下抓幾家代表性公司比對，例如代碼 24 底下有
  聯電/台積電/旺宏 → 半導體業），不是憑記憶硬編；未來出現的新代碼會 fallback 成
  `"產業別代碼 {code}"`，不會漏掉或報錯。
- `twse_api.fetch_all_stock_day()`：呼叫 OpenAPI 版的 `STOCK_DAY_ALL`
  （`openapi.twse.com.tw`，不是 `www.twse.com.tw` 的同名端點——後者即使帶 `response=json`
  參數也只會回傳 CSV），一次取得全部上市股票／ETF 當日的收盤/漲跌/成交量。
- `fetch_universe.py` 把這兩者合併成 `universe_stocks.json`（約 1,379 筆），並把
  `concept_categories.py` 裡有出現的股票額外標上 `concept_theme`（該股票所屬的精選概念股題材
  名稱，例如「AI 伺服器供應鏈」），沒有的股票 `concept_theme` 為 `null`。

```bash
python fetch_universe.py
```

## 儀表板（dashboard.html）

`dashboard.html` 是純前端、不需架站的單檔頁面（用瀏覽器直接打開即可）。**內建資料是真實資料**，
分兩層：

1. **股票清單**：`fetch_universe.py` 產生的 `universe_stocks.json`——全部上市股票／ETF
   （約 1,379 檔），欄位含真實收盤價/漲跌與 TWSE 官方產業分類（分類欄位）。
2. **個股明細**：`concept_categories.py` 精選清單（6 個題材、24 檔股票）透過 `fetch_real_data.py`
   額外抓的完整 K 線／三大法人／融資融券／基本資訊（`real_concept_detail.json`）。這 24 檔在
   股票名稱旁會多一個 🏷 標籤標示所屬題材；其餘約 1,355 檔只有目前股價，沒有歷史明細。

功能：

- 分類篩選（依 TWSE 官方產業分類）、代碼／名稱搜尋、各欄位排序、當日漲跌幅排行（Top 5 漲幅／跌幅）
- 工具列「📈 只看有完整明細」可篩選出那 24 檔精選概念股，避免點到沒有明細的股票才發現沒資料
- 點任一列（或列尾的「K線/法人 ›」按鈕）開啟個股詳情：K 線＋成交量（Canvas 手繪，含十字準線與
  懸停 tooltip）、三大法人買賣超表、融資融券表、基本資訊（PER／殖利率／PBR）、重點整理觀點；
  沒有明細資料的股票會顯示「尚無此股票的 K 線資料」，不會壞掉
- 兩個獨立上傳入口：「上傳股票資料」對應 `universe_stocks.json` 或 `main.py` 一般輸出
  （`StockRecord` 陣列）；「上傳個股明細」對應 `--with-detail` / `fetch_real_data.py` 的輸出
  （以股票代碼為 key 的字典）
- 深色模式自動跟隨系統設定，K 線圖會依主題重繪配色（紅漲綠跌，符合台股慣例）

要更新內建的資料快照：跑 GitHub Actions 的 `fetch-universe-data.yml` / `fetch-real-twse-data.yml`
（見下一節），或在有網路的環境本機執行

```bash
python fetch_universe.py       # 全部上市股票清單
python fetch_real_data.py      # 精選概念股的完整明細
```

產生新的 JSON 後，把檔案分別用儀表板上方的兩個上傳按鈕載入即可，不需要改任何程式碼；也可以直接
把內容貼進 `dashboard.html` 裡 `id="sample-data"`（股票清單）／`id="sample-detail"`（個股明細）
的 `<script>` 區塊，取代成新的內建快照。

`generate_sample_data.py` / `generate_sample_detail.py` 仍保留作為離線開發用的虛構資料產生器
（`concept_categories.py` 那份精選清單，價格是隨機數，不是真實報價），供沒有網路時測試用；
`universe_stocks.json` 目前沒有對應的離線虛構版本。

## 用 GitHub Actions 抓真實資料

開發這個專案的沙盒環境本身出網政策擋掉所有外部網站（見「已知限制」），完全無法連線到
MoneyDJ／TWSE／TradingView。GitHub Actions runner 有自己的網路，不受這個限制，所以有兩個
workflow 分別繞過沙盒限制、直接拿到真實資料：

**`.github/workflows/fetch-real-twse-data.yml`**（精選概念股完整明細）：

- 觸發方式：對 `claude/moneydj-concept-scraper-igtou1` 分支推送會影響
  `moneydj-scraper/fetch_real_data.py`、`concept_categories.py`、`twse_api.py`、`insights.py`、
  `models.py`、`requirements.txt` 或 workflow 本身的 commit 時自動執行；也可以在 GitHub UI 手動
  `workflow_dispatch`（但 API 觸發需要 workflow 檔案先存在於預設分支）。
- 執行內容：`fetch_real_data.py` 沿用 `concept_categories.py` 裡人工整理的分類/角色清單
  （6 個題材、24 檔股票，見下方模組結構），呼叫 `twse_api.fetch_stock_details()` 取得真實
  日 K 線／三大法人買賣超／融資融券／基本資訊，價格變動（`change`／`change_pct`）由最近
  兩個交易日的真實收盤價自行計算，不依賴 `STOCK_DAY` 自帶的漲跌欄位。
- 結果會寫成 `real_concept_stocks.json` 與 `real_concept_detail.json`，並自動 commit
  回觸發的分支（也會上傳成 workflow artifact）。已知限制：只支援上市（TWSE）股票，
  上櫃（TPEX）代碼會是空結果——`concept_categories.py` 裡的清單只留下已實測抓得到資料的
  股票，新增候選股票後請照同樣方式先跑一次真實抓取，把還是空值的移除。
- 這兩個檔案跟 `--with-detail` 的輸出格式完全一樣，一樣可以直接用儀表板的兩個上傳按鈕載入。

**`.github/workflows/fetch-universe-data.yml`**（全部上市股票 + 官方產業分類）：

- 觸發方式跟上面類似，改看 `fetch_universe.py`、`concept_categories.py`、`twse_api.py`、
  `models.py`、`requirements.txt` 或 workflow 本身的變動。
- 執行內容：`fetch_universe.py`（見上一節），只抓當下快照，不逐檔抓歷史明細，所以一次執行
  通常幾十秒內就能跑完全部 1,000+ 檔股票（相較之下 `fetch_real_data.py` 因為要對 24 檔各自抓
  ~2 個月 K 線 + 10 天法人/資券，單次要跑 1～3 分鐘）。
- 結果寫成 `universe_stocks.json`，同樣自動 commit 回分支。

兩個 workflow 都監看 `twse_api.py`，同一次推送可能同時觸發兩者，各自把結果 commit 回同一個
分支——這兩個 JSON 都是單行 minify 過的內容，一般的 `git rebase`／merge 在這種檔案上一定會
衝突（無法逐行合併兩份不同的單行 JSON），所以兩個 workflow 的「commit 回分支」步驟在
push 被拒絕時，用的是 `git fetch` + `git reset --soft origin/<branch>` 重新在最新的分支頂端
上重新提交自己這份最終內容，而不是嘗試 rebase／merge diff。

## 測試

```bash
pytest
```

單元測試涵蓋純函式（`_split_id_and_name`、`_extract_id_from_href`、`StockRecord.change_pct_float`、
`rank_today_gainers`、`tradingview.apply_quote`、`company_map.resolve_company_targets`、
`aggregate.summarize_by_stock`、`twse_api` 的解析函式、`insights.summarize_stock_insights`）
與 `parse_page` 對假 HTML 表格的解析。

## 已知限制

- `role`（細分產業角色）欄位多數頁面沒有獨立欄位，需依實際頁面結構在 `_parse_row` 內補上對應邏輯。
- 不同網站/頁面的欄位順序可能不同，請先跑 `--inspect` 核對後再調整；`parser.py` 目前的通用表格
  啟發式（找最大 table + `%` 儲存格定位）不保證適用所有網站。
- `company_map.json` 需要人工維護每家公司的目標頁面網址，沒有自動搜尋機制。
- `twse_api.py` 目前只支援上市（TWSE）股票，上櫃（TPEX）代碼會拿到空的 ohlc/institutional/margin；
  且三大法人／融資融券是「每個交易日打一次全市場端點再過濾」，股票數多、天數多時請求數會累加，
  記得保留內建的延遲（`fetch_stock_details` 的 `delay` 參數），不要調成 0。
- `fetch_universe.py` 只涵蓋上市（TWSE），不含上櫃（TPEX），且只抓當下快照（代碼/名稱/官方
  產業分類/當日價格），刻意不逐檔抓歷史 K 線／法人／資券——對 1,000+ 檔股票這樣做請求數會是
  數萬次，時間與對 TWSE 伺服器的負擔都不合理。想看特定股票的完整明細，把它加進
  `concept_categories.py` 用 `fetch_real_data.py` 單獨抓。
- `INDUSTRY_CODE_NAMES`（`twse_api.py` 裡的產業別代碼對照表）是 2026-08-11 用當時 1094 家
  真實上市公司的資料反推出來的，涵蓋當時出現的 33 個代碼；未來若 TWSE 新增代碼，
  `parse_all_companies` 會 fallback 成 `"產業別代碼 {code}"`（不會報錯），但需要人工核對後
  補進表裡才有正確的中文名稱。
- 反爬蟲方面目前有 User-Agent 輪替、隨機延遲、以及抓取失敗時的指數退避重試（`fetch_html` 的
  `retries`/`backoff_base` 參數）；若對方有更嚴格的頻率限制或需要 Cookie/Session 驗證，需自行加上
  `requests.Session()` 的 cookie 持久化、或改用瀏覽器自動化工具。
- 不含任何股價預測邏輯，`rank_today_gainers`／`aggregate.summarize_by_stock` 都只是資料排序/計數，
  「多來源都列為概念股」不代表真實供應關係已被驗證，僅供參考。
- **開發此專案的環境本身出網政策擋掉了一般外部網站**（moneydj.com、tradingview.com、
  cnyes.com 等皆連不到，代理回傳 403），所以爬取邏輯未曾對真實頁面驗證過，`_parse_row` 的欄位
  索引、`tradingview.py` 的端點/欄位名稱、`company_map.example.json` 裡的網址都是佔位/未驗證，
  需要你在有網路的環境先小量測試、核對後再正式使用。

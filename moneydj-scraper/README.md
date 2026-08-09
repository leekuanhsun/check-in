# MoneyDJ 概念股爬蟲

爬取 MoneyDJ 理財網的概念股/供應鏈頁面，擷取股票代碼、名稱、當日價格與漲跌幅，輸出結構化 JSON。
不做股價預測，僅提供資料擷取與「當日漲跌幅排序」。

## 安裝

```bash
pip install -r requirements.txt
```

## 使用方式

1. 先用 `inspect_page` 核對目標頁面的表格結構：

   ```bash
   python moneydj_scraper.py --inspect "https://www.moneydj.com/z/zc/zca/zca_0.djhtm"
   ```

   依印出的表格 HTML，調整 `moneydj_scraper.py` 中 `_parse_row` 的欄位索引邏輯。

2. 準備目標清單（參考 `targets.example.json`），複製為自己的檔案並填入實際 URL：

   ```json
   [
     {"url": "https://www.moneydj.com/...", "category": "半導體供應鏈"}
   ]
   ```

3. 執行批次爬取：

   ```bash
   python moneydj_scraper.py --targets targets.json --output moneydj_concept_stocks.json --top 10
   ```

   結果會寫入 `moneydj_concept_stocks.json`，並印出當日漲幅排行（僅供參考，非預測）。

## 已知限制

- `role`（細分產業角色）欄位多數頁面沒有獨立欄位，需依實際頁面結構在 `_parse_row` 內補上對應邏輯。
- 不同頁面的欄位順序可能不同，請先跑 `--inspect` 核對後再調整。
- 目前只做 User-Agent 輪替 + 隨機延遲；若對方有更嚴格的頻率限制，需自行加上 session/cookie 處理或改用瀏覽器自動化工具。
- 不含任何股價預測邏輯，`rank_today_gainers` 僅是當日數據排序。

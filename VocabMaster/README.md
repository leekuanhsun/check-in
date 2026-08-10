# 多益背單字 (VocabMaster)

一個 iOS 背單字 App，內容取自使用者提供的多益（TOEIC）單字 PDF，依照 **400 / 600 / 800 / 990** 四個分數級距分組，
每級距 25 組、每組 10 個單字（對應原 PDF 每頁 10 字），共 1000 字。

## 功能

- **分數級距首頁**：400 / 600 / 800 / 990 四張卡片，顯示各級距學習進度。
- **分組列表**：每個級距 25 組，顯示每組的熟記進度與測驗最佳成績。
- **單字卡學習**：可左右滑動瀏覽單字卡，正面顯示單字與詞性，點擊翻面顯示中文解釋、例句與例句翻譯；可標記「已熟記」。
- **發音（聲音）**：每張單字卡與單字列表都有喇叭按鈕，使用系統內建 `AVSpeechSynthesizer`（文字轉語音）朗讀單字或例句，不需下載額外音檔。
- **測驗**：每組 10 題隨機出題（英選中 / 中選英四選一），作答後即時顯示對錯，測驗結束顯示成績與答錯單字列表，並可重測。
- **進度保存**：熟記狀態與測驗最佳成績使用 `UserDefaults` 保存在裝置上。

## 專案結構

```
VocabMaster/
  VocabMaster.xcodeproj/       Xcode 專案檔（含共用 Scheme）
  VocabMaster/
    VocabMasterApp.swift       App 進入點
    Models/
      VocabWord.swift          單字資料模型
      Band.swift                400/600/800/990 級距定義
      VocabStore.swift          載入 vocab.json、管理學習進度
      Speaker.swift              AVSpeechSynthesizer 語音朗讀封裝
    Views/
      BandListView.swift        首頁：級距選擇
      GroupListView.swift       單一級距的 25 組列表
      GroupDetailView.swift     單組詳情，含「開始學習」「單字測驗」入口
      FlashcardView.swift       單字卡學習畫面
      QuizView.swift            測驗畫面與結果頁
    Resources/
      vocab.json                1000 字資料（單字、詞性、中文解釋、例句、例句翻譯、所屬分數級距）
    Assets.xcassets             App 圖示與強調色
```

## 在 Mac 上開啟與執行

此專案是在沒有 macOS/Xcode 的環境中以純文字方式產生的，尚未在 Xcode 中實際編譯驗證。請在 Mac 上依下列步驟開啟：

1. 使用 Xcode 15 以上版本開啟 `VocabMaster.xcodeproj`。
2. 選擇模擬器或實機作為執行目標。
3. 若要在實機上安裝，於 Signing & Capabilities 設定你自己的 Team 後即可執行（`Product ▸ Run`）。
4. 第一次開啟若 Xcode 提示 "Recommended Settings" 或詢問升級專案格式，允許 Xcode 自動更新即可，不影響原始碼。

若編譯出現任何錯誤，多半只是新版 Xcode 的細節設定差異，屬正常狀況，可依 Xcode 提示調整。

## 單字資料來源與處理

單字資料是從使用者上傳的 PDF（33MB／100 頁，每頁 10 字）以 `pypdf` 擷取文字後，
以程式解析出「單字 / 詞性 / 中文解釋 / 例句 / 例句中譯」五個欄位，並依 PDF 內建的分數級距側邊欄
（衝 400 分 / 衝 600 分 / 衝 800 分 / 衝 990 分）標記每個單字所屬級距。過程中修正了少數 PDF
文字擷取造成的間距亂碼，以及一個原文的拼字錯誤（`aprove` → `approve`）。

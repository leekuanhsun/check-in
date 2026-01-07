# Firebase 線上同步設定指南

本系統已內建 Firebase 同步功能，只需簡單設定即可啟用多人即時協作。

## 步驟 1: 建立 Firebase 專案
1. 前往 [Firebase Console](https://console.firebase.google.com/)。
2. 點擊 **"新增專案" (Create a project)**。
3. 輸入專案名稱 (例如: `rollcall-system`)，並依照指示完成建立。

## 步驟 2: 設定資料庫 (Firestore)
1. 在左側選單點擊 **"建構" (Build)** -> **"Firestore Database"**。
2. 點擊 **"建立資料庫" (Create database)**。
3. 選擇 **"以測試模式啟動" (Start in test mode)** (方便初期測試，任何人皆可讀寫)。
   * *注意：正式上線後建議修改規則以提升安全性*。
4. 選擇位置 (建議選 `asia-east1` 或預設值)，點擊 **"啟用" (Enable)**。

## 步驟 3: 取得設定檔 (Config)
1. 點擊左上角的 **齒輪圖示 (專案設定)** -> **"專案設定" (Project settings)**。
2. 在下方 **"您的應用程式" (Your apps)** 區塊，點擊 **`</>` (Web)** 圖示。
3. 輸入應用程式暱稱 (例如: `Web App`)，點擊 **"註冊應用程式" (Register app)**。
4. 您會看到一段 `const firebaseConfig = { ... };` 的程式碼。
5. **複製** `{ ... }` 內部的內容。

## 步驟 4: 貼上設定
1. 回到本專案資料夾。
2. 開啟 `firebase-config.js` 檔案。
3. 將您複製的內容貼上並覆蓋原有的 `YOUR_API_KEY` 等預設值。

```javascript
// 範例：
const firebaseConfig = {
    apiKey: "AIzaSyD...",
    authDomain: "rollcall-system.firebaseapp.com",
    projectId: "rollcall-system",
    storageBucket: "rollcall-system.appspot.com",
    messagingSenderId: "123456...",
    appId: "1:12345..."
};
```

## 步驟 5: 重新整理網頁
重新整理網頁後，若設定正確，頁面最下方狀態列會顯示綠色的 **「☁️ 雲端同步中」**。此時您在任何裝置上所做的操作都會即時同步！

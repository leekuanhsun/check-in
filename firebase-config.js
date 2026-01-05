// Firebase 設定檔
// 請前往 Firebase Console (https://console.firebase.google.com/)
// 1. 新增專案 (Project)
// 2. 新增網頁應用程式 (Web App)
// 3. 複製 SDK 設定與配置 (firebaseConfig) 貼上並覆蓋以下的設定物件

const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID"
};

// 初始化 Firebase (這些變數將在 script.js 中使用)
// 確保在引入 script.js 之前引入此檔案與 Firebase SDK

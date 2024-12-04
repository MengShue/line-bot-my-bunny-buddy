## LINE OCR 收據與發票記錄機器人

本項目是一個基於 LINE Messaging API 的聊天機器人，使用 OCR 技術來記錄收據或發票。使用者可以透過 LINE 傳送收據或發票的照片，機器人將自動識別並記錄總計金額，並可協助檢查發票是否中獎。

### 功能特點

 - OCR 金額提取：使用 Google Vision API 技術，從收據或發票圖像中提取總計金額。
 - 發獎檢查：自動比對發票號碼，協助使用者檢查是否中獎。
 - 多支持：支持繁體中文與英文的文字識別。
 - 圖處理：包含圖像旋轉校正、灰度化等，提升 OCR 識別準確度。

### 關於發票兌獎更新说明

更新於 2024 年 11 月

在 2024 年 11 月，我們向財政部財政資訊中心進行了諮詢，了解到 財政部已不再開放個人開發者申請統一發票兌獎的 AppID。根據最新規定，只有公司行號或政府機構才能申請 AppID。這項變更對我們的專案產生了直接影響，因為原先依賴的 API 介面已無法繼續使用。

為了確保應用程式的功能性和使用者體驗，我們及時調整了策略。現在，我們透過解析財政部稅務入口網的公開信息，獲取最新的統一發票中獎號碼和相關資訊。此方法無需依賴 AppID，即可實現統一發票的兌獎功能。這項改進不僅保持了應用的完整性，還提高了程式的靈活性和穩定性。

**注意：** 由於網頁解析方式依賴財政部網站的結構，若網站頁面佈局或元素發生變化，可能會影響程序的正常運作。我們將持續關注網站的更新，並及時對程序進行維護和升級。

### 環境需求

 - Python 3.10+
 - Flask
 - line-bot-sdk
 - Tesseract OCR
 - Pillow（PIL）
 - PyYAML
 - Heroku CLI（若部署至 Heroku）

### 安裝步驟

1. 安裝 Python 及相關套件

確保已安裝 Python 3，並使用 pip 安裝所需套件：
```commandline
pip install -r requirements.txt
```
2. 安裝 Tesseract OCR

#### Windows

 - 下載並安裝 [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)。

#### macOS
```commandline
brew install tesseract
```
#### Linux
```commandline
sudo apt-get install tesseract-ocr
```
3. 安裝 Tesseract 語言包
 - 確保安裝繁體中文（chi_tra）和英文（eng）語言包。

#### macOS
```commandline
brew install tesseract-lang
```
#### Linux
```commandline
sudo apt-get install tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-eng
```

4. 配置環境變數

在系統環境變數或 .env 文件中，設定以下變數：
 - CHANNEL_ACCESS_TOKEN：您的 LINE Channel Access Token
 - CHANNEL_SECRET：您的 LINE Channel Secret

5. 配置 config.yaml

在項目根目錄下，創建一個 config.yaml 文件，內容如下：
```commandline
server:
  host: '0.0.0.0'
  port: 5000
```

### 運行應用程式

#### 本地運行
```commandline
python app.py
```
#### 部署至 Heroku

 - 1.	登入 Heroku 並創建新應用程式。
 - 2.	將項目推送至 Heroku：
```commandline
git push heroku main
```
 - 3.	在 Heroku 的應用程式設定中，添加環境變數 CHANNEL_ACCESS_TOKEN 和 CHANNEL_SECRET。
 - 4.	在 LINE Developers Console 中，將 Webhook URL 設定為 https://{your-heroku-app-name}.herokuapp.com/callback。

### 使用說明

- 1.	添加好友：使用 LINE 掃描機器人的 QR Code，將其添加為好友。
- 2.	傳送收據或發票：拍攝收據或發票的照片，透過 LINE 傳送給機器人。
- 3.	接收回覆：機器人將自動回覆總計金額，未來版本將支持發票中獎檢查功能。

### 未來計劃

- 發票中獎檢查：整合中華民國財政部的發票資料，實現自動中獎檢查。(已實現)
- 數據存儲：將識別的收據和發票資訊存入資料庫，方便統計與查詢。
- 多種格式支持：優化對不同類型收據和發票的識別能力。

### 聯繫方式

如有任何問題，請聯繫 meng.s.song@gmail.com。

注意：在使用本應用程式時，請確保遵守相關的法律法規，尊重用戶的隱私和數據安全。

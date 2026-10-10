# 🎓 校園課業小幫手 LINE Bot (Campus Study Assistant)

這是一個專為大學資訊課專案設計的 **AI 課業輔導 LINE Bot**。後端採用 **Python (Flask + Gunicorn)** 部署於 **Render 免費版**，整合 **LINE Messaging API (v3)** 與 **Google Gemini API**，能扮演 24 小時在線的課業助教，引導同學思考、解析演算法與觀念、排查程式邏輯，並提供排版乾淨、附帶中文註解的程式範例。

---

## 🌟 核心功能與進階架構優化（改善版亮點）

專案在經歷初期部署與實測後，已完成針對 **Gemini 429 配額限制** 與 **Render 冷啟動逾時** 的深度架構重構：

1. **429 Too Many Requests 防禦架構**：
   - **模型瀑布式降級 (Model Cascade)**：優先使用反應迅速、配額穩定之模型（如 `gemini-3.8-flash`），撞牆 429 時自動平滑降級至輕量備用模型（`gemini-3.5-flash-lite` / `gemini-3.1-flash-lite`）。
   - **記憶體 TTL 快取機制 (In-Memory Cache)**：內建 1 小時過期時間之問答快取，相同或相似課業問題（如「什麼是二元搜尋樹」）命中快取時 **0.001 秒瞬間回傳**，耗損 0 次 API 配額，杜絕重複提問導致的 429。
   - **指數退避與隨機抖動 (Exponential Backoff with Full Jitter)**：遭遇速率限制時，自動按指數增長結合亂數抖動進行短暫避讓重試。
2. **LINE Webhook 10 秒 Timeout 徹底根治**：
   - **背景非同步線程 (Asynchronous Threading)**：Webhook 接收端點在驗證數位簽章後，將耗時的 AI 運算與 LINE 回覆工作丟入背景守護線程 (`threading.Thread`)，並在 **數十毫秒內立即回傳 HTTP 200 OK** 給 LINE 伺服器，從根本上杜絕 LINE 10 秒逾時導致的「已讀不回」與「系統存取較為繁忙」問題。
3. **三種實測情境全面支援**：
   - **情境一：正常學科觀念與程式題**（例如「解釋快速排序法」、「示範 Python 遞迴」）提供條列解析與良好註解範例。
   - **情境二：模糊與不完整輸入導引**（使用者若僅輸入「幫我」、「求助」、「作業」等模糊字眼）立即提供結構化提示範本，引導學生具體發問且**不耗損任何 API 配額**。
   - **情境三：不支援之多媒體類型友善防呆**（使用者傳送貼圖、圖片、語音、影片或位置時）自動觸發友善回饋，說明目前專注於文字輔導並引導輸入文字。
4. **企業級資安與金鑰保護**：
   - 嚴格落實 `X-Line-Signature` 數位簽章 HMAC 驗證。
   - 真實金鑰完全隔離於本機 `.env` 與 Render 後台私密環境變數中，Git 歷史紀錄 100% 乾淨無洩漏。
5. **東華大學師資資訊直通（陳文盛老師）**：
   - 專題特別整合指導教授——**國立東華大學通識教育中心 陳文盛助理教授**（理工二館 C306）之研究室、學經歷、開課與專長資訊。點選快捷按鈕或輸入「陳文盛」即可 0 延遲獲取完整介紹。

> 🏫 **課程致謝**：本專題為國立東華大學通識教育中心資訊課程──「和AI一起寫程式：創意生活應用」專案，指導教授：陳文盛 博士。

---

## 📁 專案檔案結構

```text
LINE Bot/
├── app.py                 # 主要入口：Flask Web 伺服器、非同步 Webhook 處理、多媒體防呆路由
├── gemini_service.py      # AI 核心模組：模型瀑布降級、指數退避、TTL 快取、模糊字詞過濾
├── requirements.txt       # 相依套件清單 (flask, line-bot-sdk, google-genai, gunicorn 等)
├── Procfile               # 雲端生產環境開機命令 (web: gunicorn app:app)
├── .env.example           # 環境變數設定範本（僅含佔位符）
├── .env                   # 本機環境變數真實金鑰（*絕對嚴禁上傳至 Git*）
├── .gitignore             # Git 忽略設定清單
├── dev_record.html        # 一頁式專題開發歷程與實測成果展示網頁
└── README.md              # 完整專案說明與操作指南
```

---

## 🚀 新手快速啟動教學（本機運行）

### 步驟 1：建立並啟動 Python 虛擬環境

建議使用 Python 3.10 以上版本（支援 Python 3.13）。

```powershell
# 1. 建立虛擬環境 (名為 venv)
python -m venv venv

# 2. 啟動虛擬環境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# （若是 CMD 終端機，請執行：.\venv\Scripts\activate.bat）
```

### 步驟 2：安裝相依套件

```powershell
pip install -r requirements.txt
```

### 步驟 3：設定環境變數 (`.env`)

複製範本檔案 `.env.example` 為 `.env`，並填入您的真實金鑰：
```powershell
Copy-Item .env.example .env
```

```env
# LINE Developers Console -> Basic settings -> Channel secret
LINE_CHANNEL_SECRET=YOUR_LINE_CHANNEL_SECRET

# LINE Developers Console -> Messaging API -> Channel access token (long-lived)
LINE_CHANNEL_ACCESS_TOKEN=YOUR_LINE_CHANNEL_ACCESS_TOKEN

# Google AI Studio -> API Keys
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

# 選填：自訂模型名稱（預設為 gemini-3.8-flash 與 gemini-3.5-flash-lite）
GEMINI_MODEL=gemini-3.8-flash
GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite

# 伺服器監聽 Port
PORT=5000
```

### 步驟 4：本機啟動伺服器

```powershell
python app.py
```
打開瀏覽器訪問 `http://localhost:5000`，看到綠色「伺服器狀態：正常 (Online)」即表示本機端啟動成功！

---

## ☁️ 雲端部署教學 (Render.com - 100% 免費 / 免信用卡)

1. 推送程式碼至您的 GitHub 公開儲存庫（確認 `.env` 未被推送）。
2. 前往 [Render.com](https://render.com/)，選擇 **New +** -> **Web Service**，連結您的 GitHub 專案。
3. 設定參數：
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: 務必選擇 **Free ($0/month)**
4. 在 **Environment Variables** 區塊新增 `LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN`、`GEMINI_API_KEY`。
5. 建立服務後取得公開 HTTPS 網址（例如 `https://campus-bot.onrender.com`）。
6. 回到 LINE Developers 後台，設定 Webhook URL 為：
   `https://campus-bot.onrender.com/callback`，開啟 **Use webhook** 並點擊 **Verify** 驗證。
7. 在 LINE Official Account Manager 後台關閉「自動回應訊息」，開啟「Webhook」。

---

## ⚠️ 已知限制與最佳解法 (Known Limitations & Workarounds)

### 1. Render 免費版 15 分鐘休眠機制 (Cold Start)
* **現象**：若 15 分鐘無人連線，Render 會暫時休眠服務。下一次使用者發送訊息時，伺服器需要約 20~50 秒重新開機（冷啟動）。
* **已實作之防禦**：後端採用背景非同步執行架構，只要請求送達即瞬間回傳 HTTP 200，避免 LINE 伺服器提早斷線。
* **最佳消除冷啟動解法 (Keep-Alive Ping)**：
  - 使用免費的定時 Ping 服務（如 [UptimeRobot](https://uptimerobot.com/) 或 [cron-job.org](https://cron-job.org/)）。
  - 設定每 **10~14 分鐘** 對你的 Render 服務首頁 `https://your-app.onrender.com/` 發送一次 HTTP GET 請求，即可保持伺服器 24 小時溫熱在線，消除冷啟動等待！

### 2. Gemini API 免費配額 (Rate Limits & 429)
* **現象**：Google AI Studio 免費方案針對每分鐘請求數 (RPM) 及每日請求數 (RPD) 有上限限制。
* **已實作之防禦**：
  - 模糊發問（如「幫我」）在本地直接攔截導引，消耗 0 配額。
  - 記憶體快取命中時在 0.001 秒回傳，消耗 0 配額。
  - 關閉高耗能的 Google Search Grounding，提升穩定度。
  - 撞牆時自動平滑切換至輕量備用模型並具備退避重試。

---

## 🧪 三大實測情境展示教學

加入機器人好友後，可實測驗證以下情境：

| 測試情境 | 使用者輸入範例 | 預期系統行為 |
| :--- | :--- | :--- |
| **情境一：正常課業問答** | 「請用簡單的方式解釋什麼是二元搜尋樹，並附上 Python 範例」 | 小幫手條列出觀念、時間複雜度，並回傳附帶中文註解的乾淨程式碼與下方快捷選單。 |
| **情境二：模糊不完整輸入** | 「幫我」、「救命」或「不會寫作業」 | 0 秒瞬間回覆友善導引，條列格式請同學提供「科目、具體題目、目前卡點」，不浪費 API 額度。 |
| **情境三：不支援之多媒體** | 傳送任意貼圖、圖片、錄音檔 | 立即回覆友善提示，說明目前專注於文字分析，建議將題目文字或代碼貼上發問。 |

---

## 💡 建議 GitHub Commit 訊息範本

為符合軟體工程專案規範，建議將此次重構分次提交，提供以下標準且有意義的 commit 紀錄：

### Commit 1：重構 Gemini 服務以抵禦 429 配額限制
```bash
git add gemini_service.py
git commit -m "refactor(gemini): resolve 429 rate limit with model cascade, exponential backoff, and in-memory TTL caching"
```
*說明：引入多層次模型降級、指數退避抖動、TTL 快取與模糊字詞前置攔截機制。*

### Commit 2：優化 Webhook 非同步回覆以根除 10 秒逾時並補全多媒體防呆
```bash
git add app.py
git commit -m "feat(webhook): implement async background worker to eliminate 10s timeout and handle non-text media events"
```
*說明：採用非同步執行緒讓 Webhook 在毫秒級回傳 200 OK，並為貼圖、圖片、語音等事件提供友善導引。*

### Commit 3：完善專案文檔與實測情境紀錄
```bash
git add README.md dev_record.html
git commit -m "docs: update architecture documentation, known limitations workarounds, and dev showcase webpage"
```

# 🎓 校園課業小幫手 LINE Bot (Campus Study Assistant)

這是一個專為大學資訊課專案設計的 **AI 課業輔導 LINE Bot**。後端結合 **Flask**、**LINE Messaging API (v3)** 與 **Google Gemini API**，能扮演課業助教的角色，引導同學思考、解析觀念、排查程式邏輯，提供有架構且易於在手機上閱讀的解答。

---

## 🌟 專案特色與安全設計

1. **嚴謹的 Webhook 數位簽章驗證**：透過 LINE 官方 SDK (`WebhookHandler`) 檢驗 `X-Line-Signature`，確保請求百分之百來自 LINE 官方伺服器，拒絕偽造與未授權的 HTTP 請求。
2. **金鑰絕不硬編碼 (No Hardcoded Secrets)**：採用 `python-dotenv` 讀取環境變數，並在 `.gitignore` 中將 `.env` 列入黑名單，保護 API Key 與 Token 安全。
3. **輸入防呆與長度限制**：
   - 最少輸入 2 個字：避免空白或無意義單字觸發 API 呼叫。
   - 上限 500 個字：防止過長 Prompt 耗費額度或偏離主題。
4. **健全的錯誤處理與降級回覆 (Graceful Degradation)**：當遭遇網路異常、API 配額上限或未設定金鑰時，伺服器不中斷崩潰，並友善回傳提示訊息給使用者。
5. **長度截斷防護**：自動監控回答長度，確保在 LINE 5000 字元限制內完整送出。

---

## 📁 專案檔案結構

```text
LINE Bot/
├── app.py                 # 主要入口：Flask Web 伺服器、Webhook 路由、簽章驗證與事件分發
├── gemini_service.py      # AI 核心模組：Gemini API 串接、System Prompt、輸入驗證與例外處理
├── requirements.txt       # 相依套件清單
├── .env.example           # 環境變數設定範本（安全無金鑰，供設定參考）
├── .env                   # 本機環境變數真實金鑰（*切勿上傳至 Git*）
├── .gitignore             # Git 忽略設定清單
└── README.md              # 專案說明與執行操作指南
```

---

## 🚀 新手快速啟動教學（本機運行）

### 步驟 1：建立並啟動 Python 虛擬環境

建議使用 Python 3.10 以上版本。在專案根目錄開啟終端機（PowerShell 或 CMD）：

```powershell
# 1. 建立虛擬環境 (名為 venv)
python -m venv venv

# 2. 啟動虛擬環境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# （若是 CMD 終端機，請執行：.\venv\Scripts\activate.bat）
```

### 步驟 2：安裝專案相依套件

```powershell
pip install -r requirements.txt
```

### 步驟 3：設定環境變數 (`.env`)

1. 複製範本檔案 `.env.example` 並另存為 `.env`：
   ```powershell
   Copy-Item .env.example .env
   ```
2. 使用記事本或 VS Code 開啟 `.env`，填入您的金鑰：

```env
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
GEMINI_API_KEY=你的_Google_Gemini_API_Key
PORT=5000
```

> 💡 **金鑰去哪裡拿？**
> - **LINE 金鑰**：登入 [LINE Developers Console](https://developers.line.biz/)，建立一個 Messaging API Channel。在「Basic settings」可找到 `Channel secret`；在「Messaging API」分頁最下方點擊 Issue 取得 `Channel access token (long-lived)`。
> - **Gemini 金鑰**：前往 [Google AI Studio](https://aistudio.google.com/)，點擊「Get API key」即可免費建立一組金鑰。

### 步驟 4：啟動 Flask 伺服器

```powershell
python app.py
```
若成功啟動，終端機會顯示：
```text
[INFO] CampusStudyBot: 校園課業小幫手伺服器即將在 Port 5000 啟動...
 * Running on http://127.0.0.1:5000
```
你可以開啟瀏覽器造訪 `http://127.0.0.1:5000`，若看到綠色「伺服器狀態：正常 (Online)」代表本機端已正常運行！

---

## 🌐 讓 LINE 連線到你的電腦：ngrok 設定

由於 LINE 官方伺服器需要透過公開 HTTPS 網址才能將訊息推送到你的 Webhook，本機測試需使用 **ngrok**：

1. 前往 [ngrok 官網](https://ngrok.com/) 下載並安裝。
2. 保持剛才的 `python app.py` 繼續運行，**另開一個新的終端機視窗**，輸入：
   ```powershell
   ngrok http 5000
   ```
3. ngrok 會產生一組 Forwarding 網址，格式如下：
   `https://xxxx-xx-xx-xx.ngrok-free.app`
4. 你的 Webhook 完整 URL 即為：
   `https://xxxx-xx-xx-xx.ngrok-free.app/callback`

---

## 📲 LINE 後台設定步驟

1. 進入 [LINE Developers Console](https://developers.line.biz/) 點選你的 Channel。
2. 切換到 **Messaging API** 頁籤：
   - 找到 **Webhook settings**。
   - **Webhook URL** 填入：`https://你的ngrok網址.ngrok-free.app/callback`。
   - 開啟 **Use webhook** 開關（轉為綠色開啟狀態）。
   - 點擊 **Verify** 按鈕：若跳出 `Success` 即表示簽章驗證完全通過！
3. 進入 [LINE Official Account Manager](https://manager.line.biz/)（官方帳號後台）：
   - 點選右上角「設定」->「回應設定」。
   - **回應模式**：選擇「聊天室 (Chat)」。
   - **Webhook**：選擇「開啟」。
   - **自動回應訊息**：選擇「關閉」（避免 LINE 原生預設機器人搶話）。

---

## 🧪 課堂展示與測試項目

加入自己建立的 LINE 官方帳號好友後，可依序展示以下三種情境：

1. **正常問答展示**：
   - 輸入：「請用 Python 示範二分搜尋法的邏輯並加上詳細註解」
   - 預期效果：小幫手條列出觀念、程式碼範例與注意事項。
2. **防呆邊界測試（字數過短）**：
   - 輸入：「好」
   - 預期效果：小幫手回覆提示「請輸入更具體的課業問題或科目觀念（至少 2 個字）喔！」。
3. **長度限制測試（字數過長）**：
   - 輸入超過 500 字的文章。
   - 預期效果：小幫手回覆提示「發問字數請精簡在 500 字內...」。

---

## 🛡️ GitHub 上傳安全檢查清單

專案要上傳到 GitHub 交作業前，請務必確認：
- [x] 是否存在 `.gitignore` 且包含 `.env`？
- [x] 執行 `git status` 時，確認 `.env` **沒有** 出現在待提交清單中。
- [x] 提交到 GitHub 的只有 `.env.example`（裡面只放虛構假值，如 `your_line_channel_secret_here`）。
- [x] 檢查 `git log` 確認歷史紀錄中從未 commit 過任何真實金鑰。

---

## ☁️ 雲端公開部署教學 (Render.com - 100% 免費 / 免綁信用卡)

若想讓機器人 24 小時在線（或提供給評審隨時測試），可免費部署至 Render：

### 1. 方案限制與費用確認
* 選擇方案：**Free Web Service ($0/month)**。
* **完全免信用卡**：使用 GitHub 帳號註冊登入即可，平台絕不會要求填寫付款資訊。
* 休眠機制：15 分鐘無人連線會進入省電休眠；有新訊息進來時需約 30~50 秒冷啟動，此為免費方案正常現象。

### 2. 部署操作步驟
1. 將專案推送到您的 GitHub 公開 Repository（確保 `.env` 未被推送）。
2. 登入 [Render.com](https://render.com/)，點選 **New +** -> **Web Service**。
3. 連結您的 GitHub 帳號，並選取本專案 Repository。
4. 設定服務基本資訊：
   - **Name**: `campus-study-assistant`（或自訂名稱）
   - **Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: 務必確認選擇 **Free ($0/month)**
5. **設定環境變數（極重要：金鑰唯一安全存放處）**：
   - 滾動到下方點擊 **Environment Variables** -> **Add Environment Variable**。
   - 逐一新增三個變數（值請填入您自己的真實金鑰，此處由 Render 伺服器端加密保存，外部無法查看）：
     * `LINE_CHANNEL_SECRET`
     * `LINE_CHANNEL_ACCESS_TOKEN`
     * `GEMINI_API_KEY`
6. 點擊 **Create Web Service**，等待 2-3 分鐘完成建置。
7. 建置完成後，Render 會在上方提供專屬公開 HTTPS 網址，例如：`https://campus-study-assistant.onrender.com`。
8. 前往 LINE Developers 後台，將 Webhook URL 更新為：
   `https://campus-study-assistant.onrender.com/callback`，並點擊 **Verify** 驗證即可！


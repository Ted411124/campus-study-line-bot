import os
import sys
import logging
from flask import Flask, request, abort
from dotenv import load_dotenv

# 解決 Windows 控制台預設編碼 (如 CP950) 輸出 Emoji 或特殊符號時的編碼錯誤
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)

from gemini_service import get_study_help

# 載入 .env 環境變數
load_dotenv()

# 設定 Logging 格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("CampusStudyBot")

# 讀取 LINE 環境變數
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET or CHANNEL_SECRET == "your_line_channel_secret_here":
    logger.warning("【提醒】LINE_CHANNEL_SECRET 尚未在 .env 中正確設定！")

if not CHANNEL_ACCESS_TOKEN or CHANNEL_ACCESS_TOKEN == "your_line_channel_access_token_here":
    logger.warning("【提醒】LINE_CHANNEL_ACCESS_TOKEN 尚未在 .env 中正確設定！")

# 初始化 LINE SDK 核心元件
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN or "")
handler = WebhookHandler(CHANNEL_SECRET or "")

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    """首頁健康檢查端點 (可用於瀏覽器驗證伺服器是否正常開機)"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>校園課業小幫手 LINE Bot</title>
        <style>
            body { font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f0f2f5; }
            .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; max-width: 450px; }
            h2 { color: #00B900; margin-bottom: 10px; }
            p { color: #555; line-height: 1.6; }
            .status { display: inline-block; padding: 6px 12px; background: #e8f5e9; color: #2e7d32; border-radius: 20px; font-weight: bold; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🎓 校園課業小幫手 LINE Bot</h2>
            <p>後端伺服器運行中！<br>Webhook 監聽端點為：<code>/callback</code></p>
            <div class="status">● 伺服器狀態：正常 (Online)</div>
        </div>
    </body>
    </html>
    """, 200


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook 接收端點：包含數位簽章驗證"""
    # 取得 LINE 傳來的簽章 Header
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        logger.warning("收到未包含 X-Line-Signature 的請求，予以拒絕。")
        abort(400)

    # 取得原始請求本文 (Raw Body)
    body = request.get_data(as_text=True)

    # 驗證數位簽章並派發事件
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("數位簽章驗證失敗 (Invalid signature)。請檢查 LINE_CHANNEL_SECRET 是否與後台一致！")
        abort(400)
    except Exception as e:
        logger.exception("處理 Webhook 請求時發生未預期錯誤: %s", str(e))
        abort(500)

    return "OK", 200


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    """處理使用者傳送的純文字訊息"""
    user_text = event.message.text
    reply_token = event.reply_token

    logger.info("收到使用者發問: %s", user_text[:30] + ("..." if len(user_text) > 30 else ""))

    # 呼叫 Gemini 服務產生課業輔導回答
    reply_text = get_study_help(user_text)

    # 透過 LINE Reply API 回覆使用者
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[
                        TextMessage(
                            text=reply_text,
                            quick_reply=QuickReply(
                                items=[
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="解釋課業概念",
                                            text="請用簡單的方式解釋一個課業概念，並舉例。",
                                        )
                                    ),
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="分析解題步驟",
                                            text="我有一道課業題想問，請先問我要題目，再一步一步引導我解題。",
                                        )
                                    ),
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="程式除錯",
                                            text="我有程式錯誤，請先問我要程式碼和錯誤訊息，再幫我逐步找原因。",
                                        )
                                    ),
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="出練習題",
                                            text="請先問我要練習的科目或主題，再出一題練習題並附解題步驟。",
                                        )
                                    ),
                                ]
                            ),
                        )
                    ]
                )
            )
        logger.info("已成功回覆使用者訊息。")
    except Exception as e:
        logger.exception("呼叫 LINE Reply API 時發生錯誤: %s", str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info("校園課業小幫手伺服器即將在 Port %d 啟動...", port)
    app.run(host="0.0.0.0", port=port, debug=False)

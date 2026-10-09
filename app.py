import os
import sys
import logging
import threading
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
    StickerMessageContent,
    ImageMessageContent,
    AudioMessageContent,
    VideoMessageContent,
    LocationMessageContent,
    FileMessageContent,
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


# ==============================================================
# 輔助函式：發送 LINE 回覆訊息 (含快捷選單)
# ==============================================================
def send_line_reply(reply_token: str, reply_text: str, include_quick_reply: bool = True):
    """透過 LINE Reply API 發送文字訊息"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            quick_reply = None
            if include_quick_reply:
                quick_reply = QuickReply(
                    items=[
                        QuickReplyItem(
                            action=MessageAction(
                                label="出練習題",
                                text="請出一道大學常見的程式設計或演算法練習題，並附上思考提示與解題步驟。",
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="解釋課業概念",
                                text="請用簡單直白的生活比喻，解釋「二分搜尋法」的核心觀念與時間複雜度。",
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="分析解題步驟",
                                text="請示範如何用步驟拆解法，分析並解決一道經典課業題目（如費氏數列遞迴優化）。",
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="常見程式除錯",
                                text="請列出大學生寫程式最常踩雷的 3 種報錯（如 IndexError、TypeError）與除錯技巧。",
                            )
                        ),
                    ]
                )

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text, quick_reply=quick_reply)]
                )
            )
        logger.info("✅ 已成功向使用者送出 LINE 回覆。")
    except Exception as e:
        logger.exception("❌ 呼叫 LINE Reply API 時發生錯誤: %s", str(e))


# ==============================================================
# 非同步處理工作線程 (解決 LINE Webhook 10 秒 Timeout 瓶頸)
# ==============================================================
def _async_process_text_message(reply_token: str, user_text: str):
    """在背景線程執行 AI 生成與 LINE 回覆，避免阻塞 Webhook 回應"""
    logger.info(f"🧵 [背景線程] 開始處理提問: {user_text[:30]}...")
    try:
        reply_text = get_study_help(user_text)
        send_line_reply(reply_token, reply_text, include_quick_reply=True)
    except Exception as e:
        logger.exception(f"❌ 背景線程處理訊息時發生未預期錯誤: {e}")
        send_line_reply(
            reply_token,
            "抱歉！系統在處理您的問題時遇到突發小異常，請稍候片刻再試一次～",
            include_quick_reply=False
        )


# ==============================================================
# 路由端點
# ==============================================================
@app.route("/", methods=["GET"])
def index():
    """首頁健康檢查端點 (可用於瀏覽器檢驗或 Uptime 監控保持喚醒)"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>校園課業小幫手 LINE Bot</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f0f2f5; }
            .card { background: white; padding: 36px; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); text-align: center; max-width: 480px; width: 90%; }
            h2 { color: #00B900; margin-bottom: 12px; font-size: 24px; }
            p { color: #555; line-height: 1.6; font-size: 15px; }
            .status { display: inline-block; padding: 8px 16px; background: #e8f5e9; color: #2e7d32; border-radius: 20px; font-weight: bold; margin-top: 18px; font-size: 14px; }
            .tip { margin-top: 20px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 14px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🎓 校園課業小幫手 LINE Bot</h2>
            <p>後端伺服器運行正常！<br>LINE Webhook 監聽端點為：<code>/callback</code></p>
            <div class="status">● 伺服器狀態：正常 (Online)</div>
            <div class="tip">提示：可搭配定時 Ping 工具每 10 分鐘訪問此頁面，防止 Render 免費版進入休眠。</div>
        </div>
    </body>
    </html>
    """, 200


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook 接收端點：驗證簽章後立刻回傳 200，杜絕 10s Timeout"""
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        logger.warning("收到未包含 X-Line-Signature 的請求，予以拒絕。")
        abort(400)

    body = request.get_data(as_text=True)

    try:
        # handler.handle 內部會調用各自的事件處理器
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("數位簽章驗證失敗 (Invalid signature)。請檢查 LINE_CHANNEL_SECRET！")
        abort(400)
    except Exception as e:
        logger.exception("處理 Webhook 請求時發生未預期錯誤: %s", str(e))
        abort(500)

    # 關鍵優化：立即在數十毫秒內回傳 200 OK 給 LINE Webhook 伺服器
    return "OK", 200


# ==============================================================
# 事件處理器 1：純文字訊息 (Text)
# ==============================================================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    """處理使用者純文字提問：丟入背景線程非同步執行"""
    user_text = event.message.text
    reply_token = event.reply_token

    logger.info("📥 收到使用者純文字訊息: %s", user_text[:30] + ("..." if len(user_text) > 30 else ""))

    # 關鍵：非同步線程處理，讓 Flask 可以毫秒級回傳 200 OK 給 LINE
    worker = threading.Thread(
        target=_async_process_text_message,
        args=(reply_token, user_text),
        daemon=True
    )
    worker.start()


# ==============================================================
# 事件處理器 2：貼圖訊息 (Sticker - 不支援媒體防呆)
# ==============================================================
@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event: MessageEvent):
    """使用者傳送貼圖時的友善導引"""
    reply_token = event.reply_token
    logger.info("📥 收到使用者貼圖訊息")
    reply_text = (
        "收到你可愛的貼圖囉！😊\n\n"
        "小幫手目前是專門回答課業問題的 AI 助教 🎓\n"
        "請直接將你想問的「課業觀念」或「程式碼題目」以文字傳送給我喔！"
    )
    threading.Thread(
        target=send_line_reply,
        args=(reply_token, reply_text, True),
        daemon=True
    ).start()


# ==============================================================
# 事件處理器 3：圖片訊息 (Image - 不支援媒體防呆)
# ==============================================================
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event: MessageEvent):
    """使用者傳送圖片時的友善導引"""
    reply_token = event.reply_token
    logger.info("📥 收到使用者圖片訊息")
    reply_text = (
        "收到你傳送的圖片囉！📷\n\n"
        "小幫手目前版本專注於文字分析與程式除錯，暫時還無法直接看圖解題 🛠️\n\n"
        "建議您可以將「題目文字」、「數學公式」或「報錯程式碼」直接複製貼上給我，我會立刻為您分析與解答！"
    )
    threading.Thread(
        target=send_line_reply,
        args=(reply_token, reply_text, True),
        daemon=True
    ).start()


# ==============================================================
# 事件處理器 4：語音訊息 (Audio - 不支援媒體防呆)
# ==============================================================
@handler.add(MessageEvent, message=AudioMessageContent)
def handle_audio_message(event: MessageEvent):
    """使用者傳送語音時的友善導引"""
    reply_token = event.reply_token
    logger.info("📥 收到使用者語音訊息")
    reply_text = (
        "收到你的語音訊息囉！🎙️\n\n"
        "小幫手目前僅支援純文字問答，請將你想發問的課業問題轉成文字傳送給我，謝謝你的配合！"
    )
    threading.Thread(
        target=send_line_reply,
        args=(reply_token, reply_text, True),
        daemon=True
    ).start()


# ==============================================================
# 事件處理器 5：其他未支援格式 (影片、位置、檔案)
# ==============================================================
@handler.add(MessageEvent, message=(VideoMessageContent, LocationMessageContent, FileMessageContent))
def handle_other_messages(event: MessageEvent):
    """其他格式訊息之通用友善提示"""
    reply_token = event.reply_token
    reply_text = (
        "收到你的附件或位置訊息囉！📌\n\n"
        "校園課業小幫手目前僅支援純文字課業問答。請直接傳送具體的科目題目或觀念文字給我喔！"
    )
    threading.Thread(
        target=send_line_reply,
        args=(reply_token, reply_text, True),
        daemon=True
    ).start()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info("校園課業小幫手伺服器即將在 Port %d 啟動...", port)
    app.run(host="0.0.0.0", port=port, debug=False)

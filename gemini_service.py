import os
import time
import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger(__name__)

# 初始化 API Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def get_study_help(user_input: str) -> str:
    """
    呼叫 Gemini API 處理課業問題，包含 Google Search Grounding 與 429 精簡重試機制
    """
    if not client:
        logger.error("GEMINI_API_KEY 未設定")
        return "系統未設定 API Key，請聯繫管理員。"

    primary_model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    fallback_model = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

    # 啟用 Google Search Grounding 搜尋連網
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )

    # 精簡重試順序（控制在 5 秒之內，避免 LINE Webhook 超時）
    attempts = [
        (primary_model, 0),    # 第1次：主力模型直接試
        (fallback_model, 2),   # 第2次：撞 429 則切換備用模型，等待 2 秒
    ]

    for model_name, wait_seconds in attempts:
        if wait_seconds > 0:
            logger.info(f"觸發防刷/退避機制，等待 {wait_seconds} 秒後嘗試模型: {model_name}...")
            time.sleep(wait_seconds)

        try:
            logger.info(f"正在使用模型 {model_name} 產生回覆...")
            response = client.models.generate_content(
                model=model_name,
                contents=user_input,
                config=config
            )
            
            if response and response.text:
                return response.text

        except APIError as e:
            if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                logger.warning(f"模型 {model_name} 遇到 429 頻率限制 (RESOURCE_EXHAUSTED)，準備切換/重試...")
                continue
            else:
                logger.error(f"呼叫 Gemini API 時發生其他 API 錯誤 ({model_name}): {e}")
                continue
        except Exception as e:
            logger.error(f"呼叫 Gemini API 時發生未知例外 ({model_name}): {e}")
            continue

    return "抱歉！目前系統存取較為繁忙，請稍候 10~20 秒再試一次～"
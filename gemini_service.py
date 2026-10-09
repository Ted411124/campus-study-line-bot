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

# 簡易快取，避免短時間內重複詢問相同問題消耗配額
CACHE = {}
CACHE_TTL = 300  # 5分鐘內相同的問題直接回傳快取

def get_study_help(user_input: str) -> str:
    """
    呼叫 Gemini API 處理課業問題，具備防刷快取、退避重試與模型切換機制
    """
    if not client:
        logger.error("GEMINI_API_KEY 未設定")
        return "系統未設定 API Key，請聯繫管理員。"

    clean_input = user_input.strip()
    
    # 1. 快取檢查
    now = time.time()
    if clean_input in CACHE:
        cached_text, timestamp = CACHE[clean_input]
        if now - timestamp < CACHE_TTL:
            logger.info("命中快取，直接回傳結果，節省 API 配額")
            return cached_text

    primary_model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    fallback_model = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

    # 啟用 Google Search Grounding 搜尋連網
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )

    # 精簡重試順序（控制總耗時在 4 秒之內，避免 LINE Webhook 10 秒超時）
    attempts = [
        (primary_model, 0),    # 第 1 次：主力模型直接嘗試
        (fallback_model, 2),   # 第 2 次：遇到 429 降級為 lite 模型，等待 2 秒
    ]

    for model_name, wait_seconds in attempts:
        if wait_seconds > 0:
            logger.info(f"觸發防刷退避，等待 {wait_seconds} 秒後重試 model: {model_name}...")
            time.sleep(wait_seconds)

        try:
            logger.info(f"正在使用模型 {model_name} 產生回覆...")
            response = client.models.generate_content(
                model=model_name,
                contents=clean_input,
                config=config
            )
            
            if response and response.text:
                result_text = response.text
                # 寫入快取
                CACHE[clean_input] = (result_text, time.time())
                return result_text

        except APIError as e:
            if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                logger.warning(f"模型 {model_name} 達到 429 頻率限制，準備切換重試...")
                continue
            else:
                logger.error(f"API 錯誤 ({model_name}): {e}")
                continue
        except Exception as e:
            logger.error(f"未知例外 ({model_name}): {e}")
            continue

    return "抱歉！目前系統存取較為繁忙，請稍候 10~20 秒再試一次～"

import os
import time
import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger(__name__)

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def get_study_help(user_input: str) -> str:
    if not client:
        return "系統未設定 API Key，請聯繫管理員。"

    clean_input = user_input.strip()
    primary_model = "gemini-3.8-flash"
    fallback_model = "gemini-3.5-flash-lite"

    # 設定低思考力度，大幅提升回應速度並減少配額消耗
    config = types.GenerateContentConfig(
        thinking_level="low"
    )

    models_to_try = [primary_model, fallback_model]

    for model_name in models_to_try:
        try:
            logger.info(f"正在嘗試呼叫模型: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=clean_input,
                config=config
            )
            if response and response.text:
                return response.text
        except APIError as e:
            logger.warning(f"模型 {model_name} 遇到 API 錯誤: {e}")
            continue
        except Exception as e:
            logger.error(f"未知錯誤: {e}")
            continue

    return "抱歉！目前系統存取較為繁忙，請稍候 10~20 秒再試一次～"

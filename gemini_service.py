import os
import logging
from google import genai
from google.genai.errors import APIError

logger = logging.getLogger(__name__)

# 初始化 Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def get_study_help(user_input: str) -> str:
    if not client:
        return "系統未設定 API Key，請聯繫管理員。"

    clean_input = user_input.strip()
    
    # 使用免費額度最穩定的正式版模型，完全不使用連網工具以節省配額
    models_to_try = ["gemini-1.5-flash", "gemini-2.5-flash"]

    for model_name in models_to_try:
        try:
            logger.info(f"正在呼叫模型: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=clean_input
            )
            if response and response.text:
                return response.text
        except APIError as e:
            logger.warning(f"模型 {model_name} 遇到 API 錯誤: {e}")
            continue
        except Exception as e:
            logger.error(f"未知錯誤 ({model_name}): {e}")
            continue

    return "抱歉！目前系統存取較為繁忙，請稍候 10~20 秒再試一次～"

import os
import sys
import logging
from typing import Optional

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

# 載入 .env 環境變數
load_dotenv()

# 設定日誌記錄
logger = logging.getLogger(__name__)

# 限制設定
MIN_INPUT_LENGTH = 2
MAX_INPUT_LENGTH = 500
MAX_LINE_MESSAGE_LENGTH = 4500

# 課業助教專屬 System Prompt
STUDY_ASSISTANT_SYSTEM_PROMPT = """你是一位大學「校園課業小幫手」AI 助教。
你的任務是協助大學生解決各學科與程式設計的課業疑問。

請遵守以下回答準則：
1. 【引導思考與結構化】：給予清晰的條列說明、邏輯觀念或解題步驟，不要只丟死板的答案。
2. 【程式碼規範】：若問題涉及程式設計，請提供排版乾淨、包含詳細中文註解的範例，並解釋核心邏輯。
3. 【手機閱讀體驗】：因使用者是在 LINE 上閱讀，請善用空行、條列符號（如 1. 2. 或 •），避免一次輸出一整大段密集文字。
4. 【語言】：請一律使用繁體中文（台灣常用詞彙，如：程式碼、專案、演算法）。
5. 【友善鼓勵】：保持親切、專業、富有鼓勵性的助教口吻。
"""

def get_study_help(user_prompt: str) -> str:
    """
    接收使用者的課業問題，進行輸入檢查後呼叫 Gemini API 產生回答。
    
    :param user_prompt: 使用者在 LINE 輸入的文字
    :return: 準備回傳給使用者的文字訊息
    """
    cleaned_input = user_prompt.strip()
    
    # 1. 輸入長度檢查防呆
    if len(cleaned_input) < MIN_INPUT_LENGTH:
        return "👋 請輸入更具體的課業問題或科目觀念（至少 2 個字）喔！例如：「請解釋什麼是二元搜尋樹」"
    
    if len(cleaned_input) > MAX_INPUT_LENGTH:
        return (
            f"⚠️ 為了保證小幫手能精準理解，發問字數請精簡在 {MAX_INPUT_LENGTH} 字內。\n"
            f"目前字數為 {len(cleaned_input)} 字，請簡化重點後再發問一次喔！"
        )

    # 2. 檢查環境變數金鑰
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.error("GEMINI_API_KEY 未設定或仍為範本預設值。")
        return "⚠️ 【系統提醒】尚未設定有效的 Gemini API Key。請專案擁有者於 .env 檔案中填入金鑰。"

    # 3. 呼叫 Gemini API
    try:
        from google import genai
        from google.genai import types

        model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model_name,
            contents=cleaned_input,
            config=types.GenerateContentConfig(
                system_instruction=STUDY_ASSISTANT_SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1500,
            ),
        )

        reply_text = response.text or "小幫手未能生成有效回答，請換個方式再問一次看看！"
        
        # 4. LINE 訊息長度安全截斷（LINE 單則文字上限為 5000 字元）
        if len(reply_text) > MAX_LINE_MESSAGE_LENGTH:
            reply_text = reply_text[:MAX_LINE_MESSAGE_LENGTH] + "\n\n...(因訊息長度上限，後續內容已省略)..."

        return reply_text.strip()

    except Exception as e:
        logger.exception("呼叫 Gemini API 時發生異常: %s", str(e))
        return "抱歉！小幫手在思考時遇到了一點連線或系統小異常，請稍候 30 秒再發問一次看看～"

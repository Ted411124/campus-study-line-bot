import os
import sys
import time
import random
import logging
import re
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv

# 解決 Windows 控制台預設編碼輸出 Emoji 或特殊符號時的編碼錯誤
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

# ==============================================================
# 1. 課業助教專屬 System Prompt
# ==============================================================
STUDY_ASSISTANT_SYSTEM_PROMPT = """你是一位大學「校園課業小幫手」AI 助教。
你的任務是協助大學生解決各學科與程式設計的課業疑問。

請遵守以下回答準則：
1. 【引導思考與結構化】：給予清晰的條列說明、邏輯觀念或解題步驟，不要只丟死板的答案。
2. 【程式碼規範】：若問題涉及程式設計，請提供排版乾淨、包含詳細中文註解的範例，並解釋核心邏輯。
3. 【手機閱讀體驗】：因使用者是在 LINE 上閱讀，請善用空行、條列符號（如 1. 2. 或 •），避免一次輸出一整大段密集文字。
4. 【語言】：請一律使用繁體中文（台灣常用詞彙，如：程式碼、專案、演算法）。
5. 【友善鼓勵】：保持親切、專業、富有鼓勵性的助教口吻。
6. 【完整作結與篇幅控制】：回答篇幅精煉適中（建議約 500~800 字），必須將列出之所有核心重點完整說明完畢並給予總結，絕對不能話說到一半中斷。

【授課與指導教授資訊（國立東華大學 陳文盛老師）】：
本課業小幫手為「國立東華大學 通識教育中心」資訊課程專題作品。
本門課程的授課教授為「陳文盛 助理教授」。若使用者詢問陳文盛老師、授課老師、指導老師或東華大學相關師資，請以親切、尊師重道的態度詳細介紹：
• 姓名職稱：陳文盛 博士（國立東華大學 通識教育中心 專任助理教授）
• 研究室位置：理工二館 C306
• 聯絡方式：電話 03-8906610 / Email: wschen@gms.ndhu.edu.tw
• 最高學歷：國立東華大學 資訊工程學系 博士、碩士；國立臺灣科技大學 電子工程技術系 學士
• 重要經歷：台灣東部地震中心專案研究員 (2017-迄今)、大漢技術學院講師 (2000-2014)
• 開設課程：初級程式設計-Python、中級程式設計-Python、初級程式設計-Scratch與Python、資訊科技與應用
• 專業領域：RFID 資料管理、熱影像辨識、YOLO 物件追蹤、智慧感測與聲學數據分析
"""

# ==============================================================
# 1.1 東華大學 陳文盛老師 專屬直通回覆 (0 延遲且 100% 準確)
# ==============================================================
def check_professor_inquiry(user_input: str) -> Optional[str]:
    """檢測使用者是否在詢問東華大學陳文盛老師，提供結構化師資介紹卡片"""
    text = user_input.strip().lower()
    keywords = ["陳文盛", "文盛老師", "指導老師", "授課老師", "任課老師", "誰是老師", "老師是誰"]
    if any(k in text for k in keywords):
        return (
            "🎓 【國立東華大學 通識教育中心 - 陳文盛 助理教授】介紹 👨‍🏫\n\n"
            "同學你好！陳文盛老師是本門課程的授課與指導教授，也是「校園課業小幫手」非常敬重與熟悉的師長喔！\n\n"
            "📌 【基本資訊】\n"
            "• 姓名：陳文盛 博士 (Chen, Wen-Sheng)\n"
            "• 職稱：通識教育中心專任助理教授\n"
            "• 研究室：理工二館 C306\n"
            "• 電話：03-8906610\n"
            "• 信箱：wschen@gms.ndhu.edu.tw\n\n"
            "🎓 【學歷背景】\n"
            "• 國立東華大學 資訊工程學系 博士\n"
            "• 國立東華大學 資訊工程學系 碩士\n"
            "• 國立臺灣科技大學 電子工程技術系 學士\n\n"
            "💼 【經歷與專長】\n"
            "• 台灣東部地震中心專案研究員 (2017 - 迄今)\n"
            "• 大漢技術學院講師 (2000 - 2014)\n"
            "• 專長：RFID 資料管理、熱影像人臉辨識、YOLO 物件追蹤、地震與聲學數據分析\n\n"
            "📚 【開設課程】\n"
            "• 初級程式設計 - Python\n"
            "• 中級程式設計 - Python\n"
            "• 初級程式設計 - Scratch 與 Python\n"
            "• 資訊科技與應用\n\n"
            "歡迎同學在課堂上認真學習，若有程式或課業問題，除了問小幫手之外，也隨時可以到理工二館 C306 向陳老師請益喔！✨"
        )
    return None

# ==============================================================
# 2. 記憶體 TTL 快取機制 (避免重複發問重複耗損 API 配額)
# ==============================================================
class SimpleTTLCache:
    """具備過期時間 (TTL) 與容量上限的記憶體快取"""
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 300):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.cache: Dict[str, Tuple[str, float]] = {}

    def _normalize_key(self, text: str) -> str:
        # 正規化文字：去除空白、標點符號與大小寫統一，增加快取命中率
        return re.sub(r'[\s\W_]+', '', text.strip().lower())

    def get(self, text: str) -> Optional[str]:
        key = self._normalize_key(text)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.info(f"⚡ [Cache Hit] 從快取直接回傳解答 (節省 1 次 Gemini API 呼叫)")
                return value
            else:
                del self.cache[key]
        return None

    def set(self, text: str, value: str):
        key = self._normalize_key(text)
        if len(self.cache) >= self.max_size:
            # 淘汰最舊的項目 (FIFO 簡化版)
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        self.cache[key] = (value, time.time())

# 初始化快取實例 (1 小時過期，容量 300 條)
_response_cache = SimpleTTLCache(ttl_seconds=3600, max_size=300)

# ==============================================================
# 3. 模糊 / 不完整輸入防呆偵測清單 (不消耗 API 配額直接導引)
# ==============================================================
VAGUE_KEYWORDS = {
    "幫我", "救我", "救命", "求助", "不會", "作業", "題目", "問題", 
    "助教", "老師", "在嗎", "hello", "hi", "嗨", "你好", "哈囉",
    "教我", "寫程式", "程式碼", "code", "問問題"
}

def check_vague_or_incomplete_input(user_input: str) -> Optional[str]:
    """檢測使用者是否只輸入模糊或不完整字眼，並立即回傳導引範本"""
    text = user_input.strip()
    
    # 字數過短 (< 2 字)
    if len(text) < 2:
        return "👋 請輸入更具體的課業問題或科目觀念（至少 2 個字）喔！例如：「請解釋什麼是二元搜尋樹」"
    
    # 模糊詞或缺乏上下文之短輸入 (< 5 字且命中模糊關鍵詞)
    clean_text = re.sub(r'[\s\W_]+', '', text.lower())
    if clean_text in VAGUE_KEYWORDS or (len(clean_text) <= 4 and any(kw in clean_text for kw in ["幫", "救", "問", "題"])):
        return (
            "👋 同學你好！我是你的「校園課業小幫手」AI 助教 🎓\n\n"
            "收到你的求助訊號了！為了能快速且精準地協助你，請依照以下格式補充問題細節喔：\n\n"
            "📌 【詢問科目】：（例如：資料結構、微積分、Python 程式設計）\n"
            "📌 【具體問題】：（例如：遞迴和迴圈有什麼差別？或貼上題目描述）\n"
            "📌 【目前的卡點】：（例如：程式跑出 IndexError、或是不知道公式怎麼推導）\n\n"
            "請直接把詳細內容發送給我，我會一步步引導你解題！"
        )
    
    # 超長字數防護 (> 600 字)
    if len(text) > 600:
        return (
            f"⚠️ 為了保證小幫手能精準解析，發問字數請控制在 600 字以內。\n"
            f"目前字數為 {len(text)} 字，請精簡提煉重點後再傳送一次喔！"
        )
        
    return None

# ==============================================================
# 4. 核心 Gemini 呼叫服務（含模型瀑布降級與指數退避抖動）
# ==============================================================
def get_study_help(user_input: str) -> str:
    """
    呼叫 Gemini API 處理課業問題，包含：
    1. 快取查核 (Cache Hit 直接回傳)
    2. 模糊輸入過濾 (零配額消耗)
    3. 模型瀑布式降級 (Primary -> Fallback -> Lite)
    4. 指數退避重試與隨機抖動 (Exponential Backoff with Jitter)
    """
    # 步驟 0: 東華大學陳文盛老師資訊直通查核 (0 延遲且 100% 精準)
    prof_reply = check_professor_inquiry(user_input)
    if prof_reply:
        return prof_reply

    # 步驟 1: 模糊與不完整輸入攔截
    vague_guide = check_vague_or_incomplete_input(user_input)
    if vague_guide:
        return vague_guide

    # 步驟 2: 查核本機快取
    cached_reply = _response_cache.get(user_input)
    if cached_reply:
        return cached_reply

    # 步驟 3: 檢查 API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_") or api_key == "YOUR_GEMINI_API_KEY":
        logger.error("GEMINI_API_KEY 未設定或為範本預設值")
        return "⚠️ 【系統提醒】尚未設定有效的 Gemini API Key。請管理員於環境變數中設定。"

    # 步驟 4: 模型瀑布降級序列 (依序嘗試速度快、配額穩定的模型)
    # 首選：環境變數自訂 或 官方推薦的高配額 Flash 模型
    primary_model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    fallback_model = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    tertiary_model = "gemini-3.1-flash-lite"

    model_cascade = [primary_model, fallback_model, tertiary_model]
    # 去除重複模型名稱保持順序
    seen = set()
    model_cascade = [m for m in model_cascade if not (m in seen or seen.add(m))]

    # 延遲設定 (非同步背景線程有充裕時間等待 429 速率窗口恢復，杜絕提前放棄)
    base_backoff_delay = 2.0  # 基礎退避秒數
    max_total_timeout = 22.0  # 總調用保護上限 (LINE reply_token 具備 30~60 秒有效期限)
    start_time = time.time()

    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError

        client = genai.Client(api_key=api_key)
        
        # 輕量快速設定：提高輸出 Token 上限至 3000，確保完整說明不被腰斬
        config = types.GenerateContentConfig(
            system_instruction=STUDY_ASSISTANT_SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=3000,
        )

        for attempt, model_name in enumerate(model_cascade):
            # 若已耗時過久，放棄嘗試避免阻塞
            if time.time() - start_time > max_total_timeout:
                logger.warning(f"⏰ 總耗時超過保護閥值 ({max_total_timeout}s)，提前中斷重試流程")
                break

            try:
                logger.info(f"🚀 [Gemini] 嘗試使用模型 {model_name} (第 {attempt + 1} 次嘗試)...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_input.strip(),
                    config=config
                )

                if response and response.text:
                    reply_text = response.text.strip()
                    # LINE 訊息長度安全截斷 (4,000 字元上限防護)
                    if len(reply_text) > 4000:
                        reply_text = reply_text[:4000] + "\n\n...(因訊息長度上限，後續內容已自動精簡)..."
                    
                    # 寫入快取
                    _response_cache.set(user_input, reply_text)
                    return reply_text

            except APIError as e:
                # 判斷是否為 429 頻率限制 / 配額耗盡 (RESOURCE_EXHAUSTED)
                is_rate_limit = (e.code == 429 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e))
                if is_rate_limit:
                    # 指數退避計算 + 隨機抖動 (Full Jitter)
                    jitter = random.uniform(0.1, 0.6)
                    backoff = (base_backoff_delay * (1.5 ** attempt)) + jitter
                    logger.warning(
                        f"⚠️ 模型 {model_name} 遭遇 429 限流 (RESOURCE_EXHAUSTED)！"
                        f"準備降級切換，等待 {backoff:.2f} 秒..."
                    )
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(f"❌ 呼叫 Gemini API 發生其他 API 錯誤 ({model_name}): {e}")
                    continue

            except Exception as e:
                logger.error(f"❌ 呼叫 Gemini API 發生未知異常 ({model_name}): {e}")
                continue

    except Exception as outer_e:
        logger.exception(f"💥 gemini_service 初始化或載入發生嚴重錯誤: {outer_e}")

    # 所有降級模型皆失敗時的優雅降級回覆 (Graceful Degradation)
    return (
        "抱歉！目前 AI 課業小幫手存取較為繁忙（API 頻率達到臨時上限）⌛\n\n"
        "小建議：\n"
        "1. 請稍候 15~30 秒後再次發送問題。\n"
        "2. 或者點選下方快捷選單換個方式發問喔！"
    )
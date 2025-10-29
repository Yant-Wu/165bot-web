from typing import List, Dict, Optional
from utils.ollama_client import OllamaClient
from utils.log import logger
from config import config

# 定義合法的意圖類型
VALID_INTENTS = ["查詢記憶", "描述事件", "詢問功能", "閒聊"]

class IntentClassifier:
    def __init__(self):
        """
        初始化意圖分類器
        從配置中獲取Ollama設定，建立用戶端
        """
        ollama_config = config["ollama"]
        self.ollama_client = OllamaClient(
            base_url=ollama_config["base_url"],
            default_model=ollama_config["web_model"]
        )
        self.system_prompt = (
            "你是一個對話意圖分類助手，請用繁體中文回答。"
            "判斷使用者輸入屬於以下四種意圖之一，只回傳中文意圖名稱，勿加解釋："
            "查詢記憶、描述事件、詢問功能、閒聊。"
        )
        
        # --- 【修改點：新增關鍵字】 ---
        # 高信號關鍵詞（若命中，視為正在描述案件而非閒聊）
        self._high_signal_keywords = [
            "銀行", "客服", "帳戶", "帳號", "轉帳", "匯款", "ATM", "異常交易", "驗證碼", "OTP",
            # 新增假客服關鍵字
            "盜刷", "訂單錯誤", "解除分期", "重複扣款",
            # 假檢警關鍵字
            "檢察官", "法院", "拘票", "地檢署", "警察", "逮捕", "不配合", "保密",
            # 假投資關鍵字
            "投資", "群組", "高報酬", "穩賺不賠", "身分證", "查帳"
        ]
        # --- 【修改結束】 ---
        
        # 每個意圖的啟發式關鍵詞（擴充以降低對少數字的依賴）
        self.intent_keywords = {
            "查詢記憶": ["記憶", "上次", "回憶", "我之前", "紀錄"],
            "描述事件": ["收到", "匯款", "轉帳", "帳戶", "付款", "被騙", "詐騙", "遭遇", "遭到"],
            "詢問功能": ["怎麼", "如何", "可以", "如何使用", "有沒有", "功能"],
            "閒聊": ["你好", "嗨", "天氣", "聊", "感覺", "笑話"]
        }
        # 啟發式判斷分數閾值（可改為從 config 讀取）
        self.heuristic_threshold = 0.15
        # 若啟發式分數差距過小視為不確定
        self.heuristic_margin = 0.06
        # 若輸入非常長（敘述性），提高對「描述事件」的偏好
        self.long_text_len = 120

    def _parse_intent_from_llm(self, raw_result: str) -> Optional[str]:
        """
        解析LLM回傳，容錯處理（嘗試匹配四種意圖名稱）
        """
        if not raw_result:
            return None
        txt = raw_result.strip()
        # 常見格式：意圖：描述事件 / 意圖: 描述事件 / 查詢記憶
        import re
        m = re.search(r"(查詢記憶|描述事件|詢問功能|閒聊)", txt)
        if m:
            return m.group(1)
        # 嘗試抽取行首或含 Intent 標籤
        m2 = re.search(r"意圖[:：\s]*([^\n\r]+)", txt)
        if m2:
            cand = m2.group(1).strip()
            for intent in VALID_INTENTS:
                if intent in cand:
                    return intent
        return None

    def _heuristic_score(self, user_input: str) -> Dict[str, float]:
        """
        對每個意圖計算簡單啟發式分數（基於關鍵詞命中比率與文字長度）
        返回 dict intent->score (0..1)
        """
        s = user_input.lower()
        words = s.split()
        scores = {}
        for intent, kws in self.intent_keywords.items():
            count = 0
            for kw in kws:
                if kw in user_input:
                    count += 1
            # 基本分：命中數 / (1 + len(kws))
            base = count / (1 + len(kws))
            # 長文加權：若為描述性長文，偏向描述事件
            if intent == "描述事件" and len(user_input) >= self.long_text_len:
                base += 0.08
            scores[intent] = min(1.0, base)
        return scores

    def classify_intent(
        self, 
        user_input: str, 
        history: List[Dict[str, str]]
    ) -> str:
        """
        判斷使用者輸入的意圖
        
        Args:
            user_input: 使用者輸入
            history: 對話歷史
        
        Returns:
            str: 意圖類型（來自VALID_INTENTS，預設「描述事件」）
        """
        try:
            # 組合訊息
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_input})
            
            # 呼叫Ollama
            raw_result = self.ollama_client.send_chat_request(messages)
            llm_intent = self._parse_intent_from_llm(raw_result) if raw_result else None
            if llm_intent:
                logger.info(f"LLM 直覺意圖：{llm_intent}（原始結果：{raw_result}）")

            # 啟發式分數作為備援或合併依據
            heuristic_scores = self._heuristic_score(user_input)
            # 選出分數最高與次高
            sorted_scores = sorted(heuristic_scores.items(), key=lambda x: x[1], reverse=True)
            top_intent, top_score = sorted_scores[0]
            second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

            # 決策邏輯：
            # 1) 若 LLM 較明確回傳其中一個 intent，且與啟發式一致或啟發式分數不衝突（差距足夠），採 LLM。
            if llm_intent:
                hs = heuristic_scores.get(llm_intent, 0.0)
                if top_intent == llm_intent or (hs >= self.heuristic_threshold or (top_score - second_score) < self.heuristic_margin):
                    # 優先 LLM，但若啟發式非常傾向其他意圖則再決定
                    intent = llm_intent
                    logger.info(f"採用 LLM 結果：{intent}（heuristic={hs:.3f}, top_score={top_score:.3f}）")
                else:
                    # 啟發式強烈指向其他意圖，使用啟發式
                    intent = top_intent
                    logger.warning(f"LLM 結果 ({llm_intent}) 與啟發式衝突，採用啟發式：{intent} (score={top_score:.3f})")
                # 特例修正（同原有邏輯）
                if intent == "查詢記憶" and len(user_input) > 40:
                    logger.warning(f"輸入長度{len(user_input)}>40，修正意圖為「描述事件」")
                    return "描述事件"
                if intent == "閒聊":
                    long_text = len(user_input) >= 30
                    hit_signal = any(kw in user_input for kw in self._high_signal_keywords)
                    if long_text or hit_signal:
                        logger.warning(f"LLM 判為閒聊但文本類型偏向事件 ({len(user_input)} 字 / hit_signal={hit_signal})，修正為「描述事件」")
                        return "描述事件"
                return intent

            # 2) 若 LLM 無法解析出意圖，採用啟發式：若 top_score 超過閾值且與次高差距明顯，採 top_intent
            if top_score >= self.heuristic_threshold and (top_score - second_score) >= self.heuristic_margin:
                intent = top_intent
                logger.info(f"採用啟發式判斷：{intent} (score={top_score:.3f})")
                if intent == "閒聊":
                    # 長文本或高信號時修正為描述事件
                    long_text = len(user_input) >= 30
                    hit_signal = any(kw in user_input for kw in self._high_signal_keywords)
                    if long_text or hit_signal:
                        logger.warning("啟發式判為閒聊但文本屬事件性，修正為描述事件")
                        return "描述事件"
                return intent

            # 3) 皆不確定時，預設保守策略為「描述事件」
            logger.warning(f"LLM 與啟發式皆不確定（llm={raw_result!r}, heuristic_top={top_intent}:{top_score:.3f}），預設「描述事件」")
            return "描述事件"
		
        except Exception as e:
             logger.error(f"意圖判斷失敗：{str(e)}")
             return "描述事件"
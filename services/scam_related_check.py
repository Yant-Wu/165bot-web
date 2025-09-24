import re
from typing import List, Dict
from utils.ollama_client import OllamaClient
from utils.log import logger
from config import config

class ScamRelatedChecker:
    def __init__(self):
        """
        初始化詐騙相關性檢查器
        """
        ollama_config = config["ollama"]
        self.ollama_client = OllamaClient(
            base_url=ollama_config["base_url"],
            default_model=ollama_config["web_model"]
        )
        self.system_prompt = (
            "你是一個判斷使用者輸入是否與詐騙主題相關的助手。"
            "請用繁體中文回答，只回覆「是」或「否」，勿加其他內容。"
        )

        # 高信號關鍵詞與樣式（本地啟發式，先於 LLM 檢查）
        self._high_signal_keywords = [
            # 金融/轉帳/帳號類
            "轉帳", "匯款", "帳戶", "銀行", "ATM", "監管帳戶", "凍結帳戶", "解除分期", "點數",
            # 司法/執法威脅
            "檢察官", "地檢署", "法院", "拘票", "傳票", "逮捕", "警察", "調查局",
            # 操控指示/恐嚇
            "不能透露", "保密", "全程監控", "不配合", "馬上逮捕", "立即轉帳", "立即匯款",
            # 詐投/保證收益
            "投資群組", "股票群組", "保證獲利", "高報酬", "穩賺不賠",
            # 社交工程/客服詐騙
            "客服", "簡訊連結", "驗證碼", "OTP", "匯款代碼", "代收貨款",
        ]
        # 連續多位數字（可能是帳號/卡號）
        self._number_like_patterns = [
            re.compile(r"\d{8,}")
        ]

    def _heuristic_match(self, text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return False
        # 關鍵詞命中
        for kw in self._high_signal_keywords:
            if kw in t:
                logger.info(f"[Heuristic] 命中關鍵詞：{kw}")
                return True
        # 數字樣式命中
        for pat in self._number_like_patterns:
            if pat.search(t):
                logger.info("[Heuristic] 命中長數字樣式（疑似帳號/卡號）")
                return True
        return False

    @staticmethod
    def _parse_llm_yes_no(raw: str) -> bool | None:
        """將 LLM 輸出嚴格解析為布林；無法判斷時回傳 None。"""
        if not raw:
            return None
        s = raw.strip().replace(" ", "").replace("\n", "").strip("。．.！!？?")
        s_lower = s.lower()
        yes_set = {"是", "yes", "y"}
        no_set = {"否", "不是", "no", "n"}
        if s in yes_set or s_lower in yes_set:
            return True
        if s in no_set or s_lower in no_set:
            return False
        # 嚴格要求單字「是/否」；其他情況無法判斷
        return None

    def is_related(
        self, 
        user_input: str, 
        history: List[Dict[str, str]]
    ) -> bool:
        """
        檢查使用者輸入是否與詐騙相關
        
        Args:
            user_input: 使用者輸入
            history: 對話歷史
        
        Returns:
            bool: 相關返回True，不相關返回False（失敗時預設True，避免漏判）
        """
        try:
            # 1) 本地啟發式先行（降低漏判）
            if self._heuristic_match(user_input):
                return True

            # 2) 呼叫 LLM 嚴格判斷
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_input})
            
            raw_result = self.ollama_client.send_chat_request(messages)
            parsed = self._parse_llm_yes_no(raw_result)
            if parsed is None:
                logger.warning(f"LLM 輸出無法判斷，原始結果：{raw_result!r}，保守視為相關")
                return True
            logger.info(f"詐騙相關性檢查（LLM）：{parsed}（原始：{raw_result}）")
            return parsed
        
        except Exception as e:
            logger.error(f"詐騙相關性檢查失敗：{str(e)}")
            return True  # 保守策略：失敗時視為相關，避免漏判
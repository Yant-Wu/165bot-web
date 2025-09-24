from typing import List, Dict
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
            if not raw_result:
                logger.warning("Ollama未返回意圖結果，預設「描述事件」")
                return "描述事件"
            
            # 清理結果（去除標點、空格）
            cleaned_result = raw_result.strip().replace("：", "").replace(":", "").replace(" ", "")
            
            # 匹配合法意圖
            for intent in VALID_INTENTS:
                if intent in cleaned_result:
                    logger.info(f"意圖判斷完成：{intent}（原始結果：{raw_result}）")
                    
                    # 特殊修正：若輸入超40字但被判為「查詢記憶」，視為「描述事件」
                    if intent == "查詢記憶" and len(user_input) > 40:
                        logger.warning(f"輸入長度{len(user_input)}>40，修正意圖為「描述事件」")
                        return "描述事件"
                    
                    return intent
            
            # 若無匹配，預設「描述事件」
            logger.warning(f"無效意圖結果：{raw_result}，預設「描述事件」")
            return "描述事件"
        
        except Exception as e:
            logger.error(f"意圖判斷失敗：{str(e)}")
            return "描述事件"
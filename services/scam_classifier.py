from typing import List, Dict
from utils.ollama_client import OllamaClient
from utils.log import logger
from config import config

# 定義合法的詐騙類型（與prompt對應，避免判斷錯誤）
VALID_SCAM_TYPES = [
    "網路購物詐騙", "假投資詐騙", "假交友(投資詐財)詐騙", "假交友(徵婚詐財)詐騙",
    "假買家騙賣家詐騙", "假中獎通知詐騙", "假求職詐騙", "假借銀行貸款詐騙",
    "假檢警詐騙", "假廣告詐騙", "釣魚簡訊(惡意連結)詐騙", "色情應召詐財詐騙",
    "騙取金融帳戶(卡片)詐騙", "虛擬遊戲詐騙", "猜猜我是誰詐騙", "無法分類"
]

class ScamClassifier:
    def __init__(self):
        """
        初始化詐騙類型分類器
        從配置中獲取Ollama設定，建立Ollama用戶端
        """
        ollama_config = config["ollama"]
        self.ollama_client = OllamaClient(
            base_url=ollama_config["base_url"],
            default_model=ollama_config["web_model"]
        )
        # 定義分類用的System Prompt（嚴格限制輸出格式）
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """
        構建詐騙分類的System Prompt（明確分類規則與輸出格式）
        
        Returns:
            str: 格式化的System Prompt
        """
        return (
            "你是一個專業的詐騙分類助手，請用繁體中文回答。"
            "根據使用者描述的事件內容，判斷該事件屬於以下哪一類詐騙，"
            "並且只回傳其中一個詐騙類型名稱，切勿多回答或解釋。"
            "以下是類型和簡短說明，請嚴格依照這些類型判斷：\n"
            "1. 網路購物詐騙：例如收到假貨、貨不對版、無法退款\n"
            "2. 假投資詐騙：例如高回報誘騙投資\n"
            "3. 假交友(投資詐財)詐騙：以交友為名誘騙投資\n"
            "4. 假交友(徵婚詐財)詐騙：以婚戀交友為名詐財\n"
            "5. 假買家騙賣家詐騙：買家詐騙賣家錢財\n"
            "6. 假中獎通知詐騙：虛假中獎詐騙\n"
            "7. 假求職詐騙：以求職為名詐財\n"
            "8. 假借銀行貸款詐騙：假借貸款詐騙\n"
            "9. 假檢警詐騙：冒充警察詐騙\n"
            "10. 假廣告詐騙：虛假廣告誘騙\n"
            "11. 釣魚簡訊(惡意連結)詐騙：簡訊釣魚連結\n"
            "12. 色情應召詐財詐騙：色情誘騙詐財\n"
            "13. 騙取金融帳戶(卡片)詐騙：騙取銀行卡資料\n"
            "14. 虛擬遊戲詐騙：遊戲內詐騙\n"
            "15. 猜猜我是誰詐騙：冒充熟人詐騙\n"
            "如果事件不屬於以上類型，請回覆『無法分類』。"
        )

    def classify_scam_type(
        self, 
        user_input: str, 
        history: List[Dict[str, str]]
    ) -> str:
        """
        根據使用者輸入與對話歷史，分類詐騙類型
        
        Args:
            user_input: 使用者當前輸入
            history: 對話歷史（格式：[{"role": "user/assistant", "content": "..."}]）
        
        Returns:
            str: 詐騙類型（來自VALID_SCAM_TYPES，預設「無法分類」）
        """
        try:
            # 組合對話訊息（System Prompt + 歷史 + 當前輸入）
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history)  # 加入對話歷史
            messages.append({"role": "user", "content": user_input})  # 加入當前輸入
            
            # 呼叫Ollama獲取分類結果
            raw_result = self.ollama_client.send_chat_request(messages)
            if not raw_result:
                logger.warning("Ollama未返回詐騙分類結果，預設「無法分類」")
                return "無法分類"
            
            # 驗證結果是否在合法類型中（避免Ollama輸出格式錯誤）
            for valid_type in VALID_SCAM_TYPES:
                if valid_type in raw_result:
                    logger.info(f"詐騙類型分類完成：{valid_type}（原始結果：{raw_result}）")
                    return valid_type
            
            # 若結果不在合法列表中，預設「無法分類」
            logger.warning(f"Ollama返回無效詐騙類型：{raw_result}，預設「無法分類」")
            return "無法分類"
        
        except Exception as e:
            logger.error(f"詐騙類型分類失敗：{str(e)}")
            return "無法分類"
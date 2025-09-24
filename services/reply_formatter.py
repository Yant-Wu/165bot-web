from typing import Optional

class ReplyFormatter:
    @staticmethod
    def should_format(
        intent: str, 
        scam_type: str, 
        answer: str
    ) -> bool:
        """
        判斷是否需要格式化回覆（僅「描述事件」且詐騙類型可分類時格式化）
        
        Args:
            intent: 使用者意圖
            scam_type: 詐騙類型
            answer: Ollama原始回答
        
        Returns:
            bool: 需要格式化返回True，否則False
        """
        # 排除拒絕類回覆（如「無法回答非詐騙問題」）
        reject_keywords = [
            "我只能回答詐騙相關問題",
            "請提供更多資訊",
            "無法明確判斷",
            "描述無法明確判斷是否為詐騙"
        ]
        if any(keyword in answer for keyword in reject_keywords):
            return False
        
        # 僅「描述事件」且詐騙類型不為「無法分類」時格式化
        return intent == "描述事件" and scam_type != "無法分類"

    @staticmethod
    def format_reply(
        scam_type: str, 
        answer: str, 
        scam_prob: str = "約 70%"
    ) -> str:
        """
        格式化回覆（加入詐騙類型、機率、查證建議）
        
        Args:
            scam_type: 詐騙類型
            answer: 分析內容
            scam_prob: 詐騙機率（預設70%）
        
        Returns:
            str: 格式化後的回覆
        """
        return f"""📌 詐騙類型：{scam_type}
📊 詐騙機率：{scam_prob}

🔍 分析內容：
{answer}

🧠 查證建議：
1. 請保留相關對話紀錄與付款證明
2. 請勿再聯繫對方或提供任何帳戶資訊
3. 若有疑慮請撥打 165 詐騙專線
"""

    @staticmethod
    def get_default_reply(intent: str) -> str:
        """
        獲取預設回覆（針對「閒聊」「詢問功能」等意圖）
        
        Args:
            intent: 使用者意圖
        
        Returns:
            str: 預設回覆
        """
        if intent == "閒聊":
            return "🤖 我是詐騙分析機器人，能協助判斷詐騙並提供風險分析。如有疑問請隨時提問！"
        elif intent == "詢問功能":
            return "🤖 我可提供以下服務：1. 分析事件是否為詐騙 2. 判斷詐騙類型 3. 提供查證建議 4. 記憶歷史分析結果。"
        elif intent == "查詢記憶":
            return "🧠 未找到您的歷史分析記錄，請先描述事件以獲取分類結果。"
        else:
            return "抱歉，我目前只能處理詐騙相關問題，請提供更多事件細節。"
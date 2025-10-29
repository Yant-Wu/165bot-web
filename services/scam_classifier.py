from typing import List, Dict
from utils.ollama_client import OllamaClient
from utils.log import logger
from config import config

# (列表不變)
VALID_SCAM_TYPES = [
    "網路購物詐騙", "假投資詐騙", "假交友(投資財)詐騙", "假交友(徵婚詐財)詐騙",
    "假買家騙賣家詐騙", "假中獎通知詐騙", "假求職詐騙", "假借銀行貸款詐騙",
    "假檢警詐騙", "假廣告詐騙", "釣魚簡訊(惡意連結)詐騙", "色情應召詐財詐騙",
    "騙取金融帳戶(卡片)詐騙", "虛擬遊戲詐騙", "猜猜我是誰詐騙",
    "假客服(盜刷/分期)詐騙",
    "無法分類"
]

# --- 【修改點 1：精煉「假中獎」關鍵字】 ---
# 移除 "中獎", "獎金", "領獎" 等中性詞彙
# 新增 "手續費", "稅金", "點擊連結", "輸入個資" 等明確的詐騙行動
SCAM_KEYWORDS_MAP = {
    "網路購物詐騙": ["一頁式", "貨到付款", "包裹", "賣家", "拒收", "幽靈包裹", "貨不對版"],
    "假投資詐騙": ["投資", "群組", "保證獲利", "穩賺不賠", "飆股", "高報酬", "老師", "外匯", "虛擬貨幣"],
    "假交友(投資財)詐騙": ["交友", "投資", "Tinder", "Omi", "穩賺", "外匯", "見面"],
    "假交友(徵婚詐財)詐騙": ["交友", "徵婚", "結婚", "老公", "老婆", "見面", "感情"],
    "假買家騙賣家詐騙": ["買家", "蝦皮", "轉帳失敗", "認證", "無法下單", "條碼"],
    # --- 這是修改過的行 ---
    "假中獎通知詐騙": ["手續費", "稅金", "點擊連結", "輸入個資", "保證金", "回饋金", "繳納", "點選"],
    "假求職詐騙": ["求職", "工作", "高薪", "輕鬆", "在家工作", "存摺", "提款卡", "人頭"],
    "假借銀行貸款詐騙": ["貸款", "銀行", "信用", "美化帳戶", "保證金", "利率"],
    "假檢警詐騙": ["檢察官", "地檢署", "警察", "逮捕", "拘票", "傳票", "監管帳戶", "偵查不公開", "洗錢"],
    "假廣告詐騙": ["廣告", "臉書", "FB", "IG", "名人推薦", "一頁式"],
    "釣魚簡訊(惡意連結)詐騙": ["簡訊", "連結", "點擊", "包裹", "電信費", "罰單", "積分", "ETF", "驗證碼"],
    "色情應召詐財詐騙": ["色情", "應召", "援交", "買點數", "保證金", "妹妹", "LINE"],
    "騙取金融帳戶(卡片)詐騙": ["金融卡", "寄送", "提供", "帳戶", "基金會", "補助"],
    "虛擬遊戲詐騙": ["遊戲", "寶物", "點數", "帳號", "買賣", "Steam"],
    "猜猜我是誰詐騙": ["猜猜我是誰", "換號碼", "急用錢", "幫我", "叔叔", "阿姨"],
    "假客服(盜刷/分期)詐騙": ["客服", "盜刷", "重複扣款", "解除分期", "訂單錯誤", "設錯", "VIP", "刷卡", "帳戶異常", "電商", "銀行"],
    "無法分類": []
}
# --- 【修改結束 1】 ---


class ScamClassifier:
    def __init__(self):
        """
        初始化詐騙類型分類器
        """
        ollama_config = config["ollama"]
        self.ollama_client = OllamaClient(
            base_url=ollama_config["base_url"],
            default_model=ollama_config["web_model"]
        )
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """
        構建詐騙分類的System Prompt（明確分類規則與輸出格式）
        """
        # (這個函式保持上一版的修改，確保 AI 知道有 16 類，並且合法流程=無法分類)
        return (
            "你是一個專業的詐騙分類助手，請用繁體中文回答。"
            "根據使用者描述的事件內容，判斷該事件屬於以下哪一類詐騙，"
            "並且只回傳其中一個詐騙類型名稱，切勿多回答或解釋。"
            "以下是類型和簡短說明，請嚴格依照這些類型判斷：\n"
            "1. 網路購物詐騙：例如收到假貨、貨不對版、無法退款\n"
            "2. 假投資詐騙：例如高回報誘騙投資\n"
            "3. 假交友(投資財)詐騙：以交友為名誘騙投資\n"
            "4. 假交友(徵婚詐財)詐騙：以婚戀交友為名詐財\n"
            "5. 假買家騙賣家詐騙：買家詐騙賣家錢財\n"
            "6. 假中獎通知詐騙：虛假中獎詐騙(通常要求支付手續費或稅金)\n" # (可選) 增加提示
            "7. 假求職詐騙：以求職為名詐財\n"
            "8. 假借銀行貸款詐騙：假借貸款詐騙\n"
            "9. 假檢警詐騙：冒充警察詐騙\n"
            "10. 假廣告詐騙：虛假廣告誘騙\n"
            "11. 釣魚簡訊(惡意連結)詐騙：簡訊釣魚連結\n"
            "12. 色情應召詐財詐騙：色情誘騙詐財\n"
            "13. 騙取金融帳戶(卡片)詐騙：騙取銀行卡資料\n"
            "14. 虛擬遊戲詐騙：遊戲內詐騙\n"
            "15. 猜猜我是誰詐騙：冒充熟人詐騙\n"
            "16. 假客服(盜刷/分期)詐騙：冒充銀行、電商客服，謊稱帳戶盜刷、訂單錯誤或設定錯誤分期付款。\n"
            "如果事件不屬於以上16種類型，或者事件描述的是政府、銀行或郵局的「正常合法流程」，也請回覆『無法分類』。"
        )

    def _heuristic_score(self, user_input: str) -> Dict[str, int]:
        """
        計算每個詐騙類型的關鍵字命中次數
        """
        scores = {scam_type: 0 for scam_type in VALID_SCAM_TYPES}
        for scam_type, keywords in SCAM_KEYWORDS_MAP.items():
            count = 0
            for kw in keywords:
                if kw in user_input:
                    count += 1
            scores[scam_type] = count
        return scores

    def classify_scam_type(
        self, 
        user_input: str, 
        history: List[Dict[str, str]]
    ) -> str:
        """
        根據使用者輸入與對話歷史，分類詐騙類型 (混合式)
        """
        try:
            # 1. LLM 判斷
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_input})
            
            raw_result = self.ollama_client.send_chat_request(messages)
            llm_scam_type = None
            if raw_result:
                for valid_type in VALID_SCAM_TYPES:
                    if valid_type in raw_result:
                        llm_scam_type = valid_type
                        break
            
            logger.info(f"LLM 判斷類型：{llm_scam_type}（原始：{raw_result}）")

            # 2. 啟發式關鍵字判斷
            heuristic_scores = self._heuristic_score(user_input)
            sorted_scores = sorted(heuristic_scores.items(), key=lambda x: x[1], reverse=True)
            heuristic_scam_type = sorted_scores[0][0]
            top_score = sorted_scores[0][1]
            
            logger.info(f"啟發式判斷類型：{heuristic_scam_type} (分數: {top_score})")

            # 3. 決策邏輯 (保持不變)
            # (因為我們修改了關鍵字，現在合法領獎的 top_score 會是 0，不會觸發規則 1)
            
            # 規則 1：如果啟發式分數很高（命中 >= 2 個關鍵字），且 LLM 判錯 (或判斷為 "無法分類")
            if top_score >= 2 and llm_scam_type != heuristic_scam_type:
                logger.warning(f"LLM 判斷 ({llm_scam_type}) 與高分啟發式 ({heuristic_scam_type}, score={top_score}) 衝突，採用啟發式。")
                return heuristic_scam_type
            
            # 規則 2：如果 LLM 有成功判斷 (且與啟發式不衝突或啟發式分數低)，採用 LLM
            if llm_scam_type and llm_scam_type != "無法分類":
                logger.info(f"採用 LLM 判斷：{llm_scam_type}")
                return llm_scam_type
            
            # 規則 3：如果 LLM 判斷為「無法分類」，但啟發式有分數 (>= 1)，採啟發式
            if (llm_scam_type == "無法分類" or llm_scam_type is None) and top_score > 0:
                 logger.info(f"LLM 無法分類，採用啟發式判斷：{heuristic_scam_type}")
                 return heuristic_scam_type
            
            # 規則 4：如果 LLM 和啟發式都沒結果
            logger.info("LLM 與啟發式皆無明確結果，回傳 LLM 結果或 '無法分類'")
            return llm_scam_type or "無法分類"

        except Exception as e:
            logger.error(f"詐騙類型分類失敗：{str(e)}")
            return "無法分類"
from typing import Optional, Tuple
import re

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
        risk_level: Optional[str] = None
    ) -> str:
        """
        格式化回覆（加入詐騙類型、風險等級、查證建議）
        
        Args:
            scam_type: 詐騙類型
            answer: 分析內容
            risk_level: 詐騙風險等級（高/低，預設高）
        
        Returns:
            str: 格式化後的回覆
        """
        # 先從原始 answer 中擷取（或推斷）風險等級，並清理重覆區塊
        derived_level, cleaned = ReplyFormatter._derive_risk_and_clean(answer)
        final_level = (risk_level or derived_level or "高")

        return f"""📌 詐騙類型：{scam_type}
📊 詐騙風險：{final_level}

🔍 分析內容：
{cleaned}

🧠 查證建議：
1. 請保留相關對話紀錄與付款證明
2. 請勿再聯繫對方或提供任何帳戶資訊
3. 若有疑慮請撥打 165 詐騙專線
"""

    @staticmethod
    def _derive_risk_and_clean(answer: str) -> Tuple[Optional[str], str]:
        """
        從原始回答中抽取風險等級（若有），並清理重覆的標題/建議區塊與機率字樣。

        規則：
        - 先移除行首的「📌 詐騙類型：...」「📊 詐騙機率/風險：...」等標題行
        - 若偵測到百分比，>=60 → 高，否則低；把原百分比替換成「高/低」或直接移除
        - 若內文已含「🧠 查證建議」段落，截斷其後內容，避免與統一建議重覆
        - 若內文已有「詐騙風險：高/低」用詞，也可作為風險來源
        """
        if not answer:
            return None, ""

        s = answer

        # 截斷重複的建議段落
        suggest_idx = s.find("🧠 查證建議")
        if suggest_idx != -1:
            s = s[:suggest_idx].rstrip()

        # 移除內嵌的類型/風險標題行
        s_lines = []
        for line in s.splitlines():
            if re.match(r"^\s*📌\s*詐騙類型\s*：", line):
                continue
            if re.match(r"^\s*📊\s*詐騙(機率|風險)\s*：", line):
                continue
            s_lines.append(line)
        s = "\n".join(s_lines).strip()

        # 尋找百分比，推斷高/低
        risk_level = None
        m = re.search(r"(\d{1,3})\s*%", answer)
        if m:
            try:
                pct = int(m.group(1))
                risk_level = "高" if pct >= 60 else "低"
            except Exception:
                pass

        # 若未由百分比取得，嘗試從文字判斷
        if risk_level is None:
            if re.search(r"(高風險|風險\s*[：:]\s*高)", answer):
                risk_level = "高"
            elif re.search(r"(低風險|風險\s*[：:]\s*低)", answer):
                risk_level = "低"

        # 將殘留的「詐騙機率」字樣正規化為「詐騙風險」，並移除數字
        s = re.sub(r"詐騙\s*機率", "詐騙風險", s)
        s = re.sub(r"(詐騙\s*風險\s*[：:]\s*)\d{1,3}\s*%", r"\1" + (risk_level or "高"), s)

        # 移除所有單獨存在的「🔍 分析內容：」標題行，避免多次格式化累加
        cleaned_lines = []
        for line in s.splitlines():
            if re.match(r"^\s*🔍\s*分析內容\s*：?\s*$", line):
                continue
            # 避免連續重覆相同行（可能是模型重複生成的標題或空白）
            if cleaned_lines and line.strip() and line.strip() == cleaned_lines[-1].strip():
                continue
            cleaned_lines.append(line)
        s = "\n".join(cleaned_lines).strip()

        # 若清理後內容為空，提供預設占位文字，避免出現空白區塊
        if not s:
            s = "（本次輸入內容過短，無法提供進一步分析。）"

        return risk_level, s

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
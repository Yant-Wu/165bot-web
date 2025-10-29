import ollama
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ResponseGenerator:
    def __init__(self, config):
        self.config = config

    # 0528 - 新增 mode 參數開始
    def generate(self, user_input, combined_data, mode="detailed"):
        if mode == "brief":
            system_prompt = """
        你是一個專業的詐騙分析助手。你收到的「資料庫內容」可能包含「詐騙案例」和「合法的官方流程」。
        請你根據這些資料，比較使用者的問題，並做出客觀的風險判斷（高/低）。

        - 如果使用者的描述符合「詐騙案例」，請指出風險並說明。
        - 如果使用者的描述符合「合法的官方流程」，請告知用戶風險低，並提醒他們注意查證管道（例如官方網站）。

        資料庫內容如下：
        """
        # 0528 - 新增 mode 參數結束

#     def generate(self, user_input, combined_data):
#         system_prompt = """
# 你是一個智能助手，根據資料庫內容分析並回答用戶的問題。請依據以下的資料做出合理的判斷，並提供可能的詐騙機率（以百分比表示）、分析過程，以及如何查證的建議。

# 你的回答應該包含：
# 1. 詐騙機率：用百分比數字描述該事件是否為詐騙的機率，格式為「XX%」，例如「該事件為詐騙的機率是 70%」。
# 2. 分析過程：根據資料庫中的資料，解釋為何會得出這個結論。
# 3. 查證建議：提供具體的查證建議，幫助用戶進一步確認該事件是否為詐騙。

# 資料庫內容如下：
# """
        user_prompt = f"請根據上述資料，回答用戶提出的問題：{user_input}"
        full_prompt = system_prompt + "\n" + combined_data + "\n" + user_prompt

        try:
            base_url = (self.config or {}).get("base_url")
            if base_url:
                os.environ.setdefault("OLLAMA_HOST", base_url)

            model = (
                (self.config or {}).get("generation_model")
                or (self.config or {}).get("model")
            )
            if not model:
                raise KeyError("generation model is not configured (expected 'generation_model' or 'model')")

            output = ollama.generate(model=model, prompt=full_prompt)
            text = output["response"]

            # 後處理：將任何「機率/百分比」改為風險等級（高/低），並統一欄位名稱
            try:
                import re
                s = text
                # 將「詐騙機率」欄位名改為「詐騙風險」
                s = re.sub(r"詐騙\s*機率", "詐騙風險", s)
                # 擷取百分比（若模型仍輸出），依閾值映射為高/低，並移除數字
                # 閾值：>= 60% → 高，否則低
                m = re.search(r"(\d{1,3})\s*%", s)
                if m:
                    pct = int(m.group(1))
                    level = "高" if pct >= 60 else "低"
                    s = re.sub(r"：?\s*\d{1,3}\s*%", f"：{level}", s)
                # 若沒有百分比但寫了「風險等級：」之類的描述，嘗試規範成「高/低」
                # 若偵測不到「高/低」，預設使用「高」作為保守提示
                if ("詐騙風險" in s) and ("高" not in s and "低" not in s):
                    s = re.sub(r"(詐騙風險\s*[:：]\s*).*", r"\1高", s)
                return s
            except Exception:
                return text
        except Exception as e:
            logger.error(f"生成回答時發生錯誤：{e}")
            return "⚠️ 無法生成回答，請稍後再試。"
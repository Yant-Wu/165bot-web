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
        你是一個詐騙識別助手，請根據資料庫內容簡要回答問題，提供詐騙機率與一兩句分析，避免冗長內容。

        回答格式如下：
        詐騙機率：XX%
        原因簡述：......
        資料庫內容如下：
        """
        else:
            system_prompt = """
        你是一個智能助手，根據資料庫內容分析並回答用戶的問題。請依據以下的資料做出合理的判斷，並提供可能的詐騙機率（以百分比表示）、分析過程，以及如何查證的建議。

        你的回答應該包含：
        1. 詐騙機率：用百分比數字描述該事件是否為詐騙的機率，格式為「XX%」，例如「該事件為詐騙的機率是 70%」。
        2. 分析過程：根據資料庫中的資料，解釋為何會得出這個結論。
        3. 查證建議：提供具體的查證建議，幫助用戶進一步確認該事件是否為詐騙。

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
            # 0528
            return output["response"]
        except Exception as e:
            logger.error(f"生成回答時發生錯誤：{e}")
            return "⚠️ 無法生成回答，請稍後再試。"
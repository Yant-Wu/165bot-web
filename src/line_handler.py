import logging
import os
try:
    import certifi
    _CA_PATH = certifi.where()
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _CA_PATH)
    os.environ.setdefault("SSL_CERT_FILE", _CA_PATH)
    os.environ.setdefault("CURL_CA_BUNDLE", _CA_PATH)
except Exception:
    _CA_PATH = None
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class LineHandler:
    def __init__(self, config, query_engine, response_generator):
        self.config = config
        self.query_engine = query_engine
        self.response_generator = response_generator
        self.handler = WebhookHandler(config["line"]["channel_secret"])
        if _CA_PATH:
            self.configuration = Configuration(
                access_token=config["line"]["channel_access_token"],
                ssl_ca_cert=_CA_PATH
            )
        else:
            self.configuration = Configuration(access_token=config["line"]["channel_access_token"])
        
        # 修改：使用 lambda 正確綁定 handle_text_message
        self.handler.add(MessageEvent, message=TextMessageContent)(lambda event: self.handle_text_message(event))

    def handle_webhook(self, body, signature):
        try:
            self.handler.handle(body, signature)
            logger.info("Webhook 處理成功")
            return True
        except InvalidSignatureError:
            logger.error("簽名驗證失敗")
            return False
        except Exception as e:
            logger.error(f"處理 Webhook 時發生錯誤：{e}")
            return False

    def handle_text_message(self, event):
        """處理用戶發送的文字訊息"""
        user_input = event.message.text.strip()
        # LINE Webhook 驗證：若是 LINE Console verify 的 user_id，直接回 'OK'
        try:
            verify_user_id = (self.config.get("line", {}) or {}).get("verify_user_id", "")
            source_user_id = getattr(getattr(event, "source", None), "user_id", None)
            if verify_user_id and source_user_id == verify_user_id:
                self.reply_message(event.reply_token, "OK")
                return
        except Exception:
            # 安全起見，不因驗證流程影響正常訊息處理
            pass
        logger.info(f"收到用戶訊息：{user_input}")

        if not user_input:
            self.reply_message(event.reply_token, "⚠️ 請輸入問題。")
            return
        
        if len(user_input) > 1000:
            self.reply_message(event.reply_token, "⚠️ 輸入過長，請簡化問題。")
            return

        combined_data = self.query_engine.query(user_input)
        if not combined_data:
            # 後備策略：向量庫目前無資料或查無結果，改以使用者敘述作為上下文進行簡短分析
            fallback_context = (
                "（資料庫目前無可用文件；請僅根據使用者敘述判斷是否為詐騙，並提供簡短理由與建議。）\n"
                f"使用者敘述：{user_input}"
            )
            answer = self.response_generator.generate(user_input, fallback_context, mode="brief")
            self.reply_message(event.reply_token, answer)
            return

        # answer = self.response_generator.generate(user_input, combined_data)
        # 0528 - 呼叫 generate 時加入 mode="brief" 讓 LINE 回覆簡短開始
        answer = self.response_generator.generate(user_input, combined_data, mode="brief")
        # 0528 - 呼叫 generate 時加入 mode="brief" 讓 LINE 回覆簡短結束
        self.reply_message(event.reply_token, answer)

    def reply_message(self, reply_token, text):
        """回應用戶訊息"""
        try:
            with ApiClient(self.configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=text)]
                    )
                )
            logger.info(f"回覆訊息：{text[:50]}...")
        except Exception as e:
            logger.error(f"回覆訊息時發生錯誤：{e}")
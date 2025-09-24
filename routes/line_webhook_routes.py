from flask import Blueprint, request
from utils.log import logger
from src.line_handler import LineHandler
from src.query_engine import QueryEngine
from src.response_generator import ResponseGenerator
from src.data_loader import DataLoader
from config import config

# 建立Blueprint
line_bp = Blueprint("line", __name__)
alias_bp = Blueprint("line_alias", __name__)

# 初始化Line Bot相關模組
data_loader = DataLoader(config)
data_loader.load_embeddings()  # 載入嵌入資料
# 建立Line專用的查詢引擎與回應生成器（從配置獲取參數）
line_ollama_config = config["ollama"]["line"]
line_query_engine = QueryEngine(data_loader.get_collection(), line_ollama_config)
line_response_generator = ResponseGenerator(line_ollama_config)
# 初始化Line Handler
line_handler = LineHandler(config, line_query_engine, line_response_generator)

@line_bp.route("/webhook", methods=["POST"])
def webhook():
    """
    Line Webhook路由：處理Line使用者訊息
    驗證Line簽章，並轉發到LineHandler處理
    """
    try:
        # 1. 提取Line請求參數
        signature = request.headers.get("X-Line-Signature", "")
        request_body = request.get_data(as_text=True)
        
        logger.info("收到Line Webhook請求")
        
        # 2. 交由LineHandler處理
        if line_handler.handle_webhook(request_body, signature):
            logger.info("Line Webhook處理成功")
            return "OK", 200
        else:
            logger.warning("Line Webhook處理失敗（簽章無效或請求錯誤）")
            return "Invalid request", 400
    
    except Exception as e:
        logger.error(f"處理Line Webhook失敗：{str(e)}", exc_info=True)
        return "Internal Server Error", 500


@alias_bp.route('/webhook', methods=['POST'])
def webhook_alias():
    try:
        signature = request.headers.get("X-Line-Signature", "")
        request_body = request.get_data(as_text=True)
        logger.info("收到Line Webhook請求（/webhook 別名）")
        if line_handler.handle_webhook(request_body, signature):
            logger.info("Line Webhook處理成功（/webhook 別名）")
            return "OK", 200
        else:
            logger.warning("Line Webhook處理失敗（簽章無效或請求錯誤, /webhook 別名）")
            return "Invalid request", 400
    except Exception as e:
        logger.error(f"處理Line Webhook失敗（/webhook 別名）：{str(e)}", exc_info=True)
        return "Internal Server Error", 500
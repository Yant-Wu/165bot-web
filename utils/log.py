import logging
from datetime import datetime

def init_logger() -> logging.Logger:
    """
    初始化全域日誌系統
    設定日誌等級為INFO，格式包含時間、等級、訊息，便於問題追蹤
    
    Returns:
        logging.Logger: 配置完成的日誌物件
    """
    # 自定義日誌格式
    log_format = "%(asctime)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s"
    # 初始化日誌
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(f"scam_analyzer_{datetime.now().strftime('%Y%m%d')}.log"),  # 儲存到檔案
            logging.StreamHandler()  # 列印到控制台
        ]
    )
    return logging.getLogger(__name__)

# 建立全域可引用的日誌物件
logger = init_logger()
import os
import csv
from datetime import datetime
from typing import Optional
from utils.log import logger
from config.paths import CSV_LOG_PATH

class CSVLogger:
    def __init__(self, log_path: str = CSV_LOG_PATH):
        """
        初始化CSV日誌器（記錄使用者輸入、詐騙類型、縣市、時間）
        
        Args:
            log_path: CSV日誌檔路徑
        """
        self.log_path = log_path
        # 初始化CSV檔（若不存在則建立並寫入標題行）
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "county", "user_input", "scam_type"])
            logger.info(f"建立新的CSV日誌檔：{self.log_path}")

    def log_scam(
        self, 
        user_input: str, 
        scam_type: str, 
        county: str
    ) -> bool:
        """
        寫入詐騙紀錄到CSV
        
        Args:
            user_input: 使用者輸入（清理換行符）
            scam_type: 詐騙類型
            county: 縣市
        
        Returns:
            bool: 寫入成功返回True，失敗返回False
        """
        try:
            # 清理使用者輸入（去除換行符，避免CSV格式錯誤）
            cleaned_input = user_input.replace("\n", " ").replace("\r", " ")
            # 取得當前時間（格式：YYYY-MM-DD HH:MM:SS）
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 寫入CSV（追加模式）
            with open(self.log_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, county, cleaned_input, scam_type])
            
            logger.info(f"成功寫入CSV日誌：{timestamp} | {county} | {scam_type}")
            return True
        
        except Exception as e:
            logger.error(f"寫入CSV日誌失敗：{str(e)}")
            return False

# 說明：
# - 寫入 CSV 檔案（用於日誌或離線統計）
# - 檢查點：
#   - 檔案路徑與輪替策略（append / 日誌分檔）
#   - 欄位順序是否與 DataMerger 期望一致
#   - 檔案鎖定/並發寫入處理
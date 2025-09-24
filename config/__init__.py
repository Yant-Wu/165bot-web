"""
配置模組 - 載入YAML配置檔案和環境變數
"""
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入.env檔案
load_dotenv()

# 取得config目錄路徑
CONFIG_DIR = Path(__file__).parent

def load_config():
    """載入YAML配置檔案並合併環境變數"""
    config_file = CONFIG_DIR / "config.yaml"
    
    # 載入YAML配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 從環境變數更新敏感資訊
    if "line" in config:
        config["line"]["channel_access_token"] = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        config["line"]["channel_secret"] = os.getenv("LINE_CHANNEL_SECRET", "")
        # 可選：在 LINE Console 驗證 Webhook 時使用的使用者ID
        verify_user_id = os.getenv("LINE_VERIFY_USER_ID", config["line"].get("verify_user_id", ""))
        config["line"]["verify_user_id"] = verify_user_id
    
    if "mysql" in config:
        config["mysql"]["user"] = os.getenv("MYSQL_USER", "")
        config["mysql"]["password"] = os.getenv("MYSQL_PASSWORD", "")
        config["mysql"]["host"] = os.getenv("MYSQL_HOST", config["mysql"].get("host", "localhost"))
    
    return config

# 載入配置，供其他模組匯入使用
config = load_config()
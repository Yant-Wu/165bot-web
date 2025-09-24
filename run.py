from app import create_app
from config import config
from utils.log import logger

def main():
    """
    應用入口函數：建立應用並啟動伺服器
    """
    # 1. 建立Flask應用
    app = create_app()
    
    # 2. 從配置獲取伺服器參數
    server_config = config["server"]
    host = server_config["host"]
    port = server_config["port"]
    debug = server_config.get("debug", False)  # 除錯模式（生產環境關閉）
    
    # 3. 啟動伺服器
    logger.info(f"啟動伺服器：http://{host}:{port} | debug={debug}")
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False  # 避免重載時重複初始化模組
    )

if __name__ == "__main__":
    main()
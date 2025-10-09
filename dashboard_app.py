"""
此檔案為舊版獨立 dashboard server，已停用。
請使用 main-165project 中的 routes/api_routes.py 提供的 /fraud-stats 等 API 作前端資料來源。
若確實需要獨立啟動 dashboard，請將前端靜態/模板整合到主 Flask app，避免同時啟動多個 Flask 實例。

保留此檔案僅供參考或備份，如確定不需要可直接刪除。
"""
import sys
from utils.log import logger

def main():
    logger.warning("dashboard_app.py 已停用。請改用主應用的 API（routes/api_routes.py）。")
    print("dashboard_app.py 已停用。請改用主應用的 API（routes/api_routes.py）。")
    print("若要刪除此檔案，請確認沒有其他程式依賴它後再移除。")

if __name__ == "__main__":
    main()

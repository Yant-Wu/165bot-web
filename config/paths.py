import os

# 儲存目錄路徑
STORAGE_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../storage"))

# 資料目錄
DATA_DIR = os.path.join(STORAGE_BASE_DIR, "data")

# 具體文件路徑
TAIWAN_MAP_PATH = os.path.join(DATA_DIR, "taiwan-map.json")  # 台灣地圖數據
CITY_STATISTICS_PATH = os.path.join(DATA_DIR, "city_statistics.json")  # 城市統計數據
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.pkl")  # 嵌入向量文件
EMBEDDINGS_V2_PATH = os.path.join(DATA_DIR, "embeddings_2.pkl")  # 新版本嵌入向量

# Chroma向量資料庫路徑
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")

# 日誌文件默認路徑（如果CSV日誌需要指定位置）
CSV_LOG_PATH = os.path.join(STORAGE_BASE_DIR, "scam_logs.csv")
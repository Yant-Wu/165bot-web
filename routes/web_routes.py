from flask import Blueprint, send_from_directory, jsonify, current_app
from utils.log import logger
from config import config

# 建立Blueprint（用於註冊到Flask應用）
web_bp = Blueprint("web", __name__)
# 從配置中獲取靜態檔案路徑
STATIC_FOLDER = None

@web_bp.route("/")
@web_bp.route("/home")
def home():
    """
    首頁路由（返回home.html）
    """
    folder = current_app.static_folder
    return send_from_directory(folder, "home.html")

@web_bp.route("/chat")
def chat():
    """
    聊天頁面路由（返回chat.html）
    """
    folder = current_app.static_folder
    return send_from_directory(folder, "chat.html")

@web_bp.route("/dashboard")
def dashboard():
    """
    儀表板路由（返回dashboard.html）
    """
    folder = current_app.static_folder
    return send_from_directory(folder, "dashboard.html")

@web_bp.route("/static/<path:path>")
def serve_static(path):
    """
    靜態檔案路由（CSS、JS、圖片等）
    設定快取時間為1年（31536000秒），提升效能
    """
    try:
        folder = current_app.static_folder
        response = send_from_directory(folder, path)
        response.headers["Cache-Control"] = "max-age=31536000"
        return response
    except Exception as e:
        logger.error(f"提供靜態檔案失敗：{path} | 錯誤：{str(e)}")
        return jsonify({"error": "檔案不存在"}), 404
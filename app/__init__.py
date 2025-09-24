from flask import Flask
from pathlib import Path
from flask_cors import CORS
from config import config
from routes.web_routes import web_bp
from routes.api_routes import api_bp
from routes.line_webhook_routes import line_bp, alias_bp
from utils.log import logger

def create_app() -> Flask:
    """
    建立並配置Flask應用實例（工廠模式）
    """
    # 建立Flask應用
    # 設定 static 為專案根目錄下的 static（避免相對於 app/ 造成 404）
    base_dir = Path(__file__).resolve().parent.parent
    static_folder = base_dir / config["server"]["static_folder"]
    app = Flask(__name__, static_folder=str(static_folder))
    
    # 配置CORS
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True
    )
    logger.info("已配置CORS")
    
    # 註冊路由Blueprint
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(line_bp, url_prefix='/line')
    app.register_blueprint(alias_bp)  # /webhook 無前綴別名
    logger.info("已註冊所有路由Blueprint")
    
    return app

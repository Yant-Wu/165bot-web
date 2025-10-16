import argparse
import sys
import os
from datetime import datetime
from typing import Optional
import textwrap
import re

# ensure project root is on sys.path so "from config import config" works when running the script directly
project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import config
from utils.log import logger
from storage.mysql_logger import MySQLLogger

try:
    import pymysql
    from pymysql.cursors import DictCursor
except Exception:
    pymysql = None

TEST_SCAM_TYPE = "__TEST_DB__"

def load_env_overrides(env_path: Optional[str] = None) -> dict:
    """
    嘗試讀取專案 .env（若存在），回傳 dict 的 key->value。
    支援註解行（以 # 或 // 開頭）與去除外圍引號。
    """
    overrides = {}
    if not env_path:
        # 預設：tools/../.env
        env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    try:
        if not os.path.exists(env_path):
            return overrides
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                # 移除外層引號（單雙皆可）
                if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                    v = v[1:-1]
                overrides[k] = v
    except Exception as e:
        logger.warning(f"讀取 .env 時發生錯誤：{e}")
    return overrides

def get_mysql_cfg():
    # 先取 config 預設
    mysql_cfg = config.get("mysql", {}) if isinstance(config, dict) else config.get("mysql", {})
    # 嘗試讀取 .env 覆蓋
    env_overrides = load_env_overrides()
    host = env_overrides.get("MYSQL_HOST") or mysql_cfg.get("host") or mysql_cfg.get("HOST") or env_overrides.get("MYSQL_HOST")
    port = env_overrides.get("MYSQL_PORT") or mysql_cfg.get("port") or mysql_cfg.get("PORT")
    user = env_overrides.get("MYSQL_USER") or mysql_cfg.get("user") or mysql_cfg.get("USER")
    password = env_overrides.get("MYSQL_PASSWORD") or mysql_cfg.get("password") or mysql_cfg.get("PASSWORD")
    db_name = env_overrides.get("MYSQL_DB_NAME") or mysql_cfg.get("db_name") or mysql_cfg.get("database") or env_overrides.get("MYSQL_DB_NAME")
    enabled_env = env_overrides.get("MYSQL_ENABLED")
    enabled = None
    if enabled_env is not None:
        enabled = enabled_env.lower() in ("1", "true", "yes", "y", "on")
    else:
        enabled = bool(mysql_cfg.get("enabled", True))

    # 整理回傳結構（保留原來腳本期望的 key）
    try:
        port_int = int(port) if port is not None else 3306
    except Exception:
        port_int = 3306

    return {
        "host": host or "localhost",
        "port": port_int,
        "user": user,
        "password": password,
        "db_name": db_name or "scam_logs_db",
        "enabled": enabled
    }

def suggest_crypto_fix():
    """
    回傳針對 caching_sha2_password / sha256_password 需要 cryptography 的修復建議字串
    """
    msg = textwrap.dedent("""
    連線失敗原因可能為 MySQL 帳號使用 caching_sha2_password 或 sha256_password 的驗證方式，
    PyMySQL 在此情況下需要安裝 'cryptography' 套件。
    
    建議作法 (優先)：
    1) 安裝 cryptography：
       - 建議先更新 pip 與 wheel：
         pip3 install -U pip setuptools wheel
       - 然後安裝 cryptography：
         pip3 install cryptography
       macOS 如遇到編譯問題，先安裝 openssl：
         brew install openssl pkg-config
         export LDFLAGS="-L$(brew --prefix openssl)/lib"
         export CPPFLAGS="-I$(brew --prefix openssl)/include"
         pip3 install cryptography

    若無法安裝 cryptography 或短期替代方案：
    2) 在 MySQL 管理端將該使用者改回 mysql_native_password：
       -- 以有權限的帳號登入 MySQL，並執行：
       ALTER USER 'your_user'@'host' IDENTIFIED WITH mysql_native_password BY 'your_password';
       FLUSH PRIVILEGES;
    注意：改用 mysql_native_password 為權宜之計，請評估安全性。

    安裝完 cryptography 後，重新執行本工具即可。
    """).strip()
    return msg

def check_via_pymysql(cfg):
    if pymysql is None:
        print("pymysql 未安裝，無法使用直接 DB 查詢。請安裝 pymysql 或使用 --test-insert 檢查。")
        return None

    try:
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            charset="utf8mb4",
            connect_timeout=3,
            cursorclass=DictCursor
        )
    except Exception as e:
        # 偵測是否為 cryptography / auth plugin 相關錯誤，並提供具體建議
        msg = str(e)
        if re.search(r"cryptography|caching_sha2_password|sha256_password", msg, re.IGNORECASE):
            print("偵測到與 MySQL 驗證插件或 cryptography 相關的錯誤：")
            print(msg)
            print()
            print(suggest_crypto_fix())
            return {"connected": False, "error": msg}
        # 其他錯誤照原邏輯回傳
        return {"connected": False, "error": str(e)}

    result = {"connected": True, "database_exists": False, "table_exists": False, "record_count": 0, "recent": []}
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES LIKE %s", (cfg["db_name"],))
            result["database_exists"] = bool(cur.fetchone())

            if result["database_exists"]:
                cur.execute(f"USE `{cfg['db_name']}`;")
                cur.execute("SHOW TABLES LIKE 'scam_logs';")
                result["table_exists"] = bool(cur.fetchone())
                if result["table_exists"]:
                    try:
                        cur.execute("SELECT COUNT(*) AS cnt FROM scam_logs;")
                        row = cur.fetchone()
                        result["record_count"] = int(row["cnt"]) if row and "cnt" in row else 0
                    except Exception as e_cnt:
                        result["record_count"] = None
                        logger.warning(f"查詢筆數失敗：{e_cnt}")
                    try:
                        cur.execute("SELECT id, timestamp, county, scam_type, LEFT(user_input,200) AS snippet FROM scam_logs ORDER BY id DESC LIMIT 5;")
                        recent = cur.fetchall()
                        result["recent"] = recent
                    except Exception as e_sel:
                        logger.warning(f"查詢最近紀錄失敗：{e_sel}")
        return result
    finally:
        try:
            conn.close()
        except Exception:
            pass

def main(test_insert: bool, cleanup: bool):
    cfg = get_mysql_cfg()
    print("使用的 MySQL 設定：", {k: v for k, v in cfg.items() if k != "password"})

    mysql_logger = MySQLLogger()
    print("\n1) 嘗試透過 MySQLLogger 初始化（建立 DB / table）...")
    init_result = mysql_logger.init_db()
    print("init_db result:", init_result)

    if test_insert:
        print("\n2) 執行測試寫入（使用 scam_type='__TEST_DB__'）...")
        ok = mysql_logger.log_scam(f"測試寫入 {datetime.now().isoformat()}", TEST_SCAM_TYPE, "測試縣市")
        print("log_scam returned:", ok)

    print("\n3) 使用 pymysql 直接檢查資料庫狀態與最近紀錄：")
    pymysql_result = check_via_pymysql(cfg)
    if pymysql_result is None:
        print("跳過 pymysql 檢查（pymysql 套件缺失）")
        return

    if not pymysql_result["connected"]:
        print("無法連線到 MySQL：", pymysql_result.get("error"))
        return

    print(f"connected: {pymysql_result['connected']}")
    print(f"database_exists: {pymysql_result['database_exists']}")
    print(f"table_exists: {pymysql_result['table_exists']}")
    print(f"record_count: {pymysql_result['record_count']}")
    print("recent (last 5):")
    for r in pymysql_result.get("recent", []):
        print(f"  id={r.get('id')} time={r.get('timestamp')} county={r.get('county')} type={r.get('scam_type')} snippet={r.get('snippet')!s}")

    if cleanup:
        print("\n4) 執行清除測試紀錄（scam_type='__TEST_DB__'）...")
        try:
            conn = pymysql.connect(
                host=cfg["host"],
                port=cfg["port"],
                user=cfg["user"],
                password=cfg["password"],
                database=cfg["db_name"],
                charset="utf8mb4",
                connect_timeout=3,
                cursorclass=DictCursor
            )
            with conn.cursor() as cur:
                cur.execute("DELETE FROM scam_logs WHERE scam_type=%s", (TEST_SCAM_TYPE,))
                deleted = cur.rowcount
            conn.commit()
            conn.close()
            print(f"已刪除 {deleted} 筆測試紀錄。")
        except Exception as e:
            print("刪除測試紀錄失敗：", e)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="檢查 MySQL 資料庫/表是否存在，並列出最近紀錄。")
    p.add_argument("--test-insert", action="store_true", help="寫入一筆測試紀錄（scam_type='__TEST_DB__'）")
    p.add_argument("--cleanup", action="store_true", help="刪除測試紀錄（scam_type='__TEST_DB__'）")
    args = p.parse_args()
    main(test_insert=args.test_insert, cleanup=args.cleanup)

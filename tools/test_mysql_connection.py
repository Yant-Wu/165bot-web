import argparse
import time
from datetime import datetime
from utils.log import logger
from storage.mysql_logger import MySQLLogger
import pymysql
from config import config

TEST_SCAM_TYPE = "__TEST_MYSQL__"

def verify_in_db(mysql_cfg, scam_type):
    try:
        conn = pymysql.connect(
            host=mysql_cfg["host"],
            port=int(mysql_cfg.get("port", 3306)),
            user=mysql_cfg["user"],
            password=mysql_cfg["password"],
            database=mysql_cfg["db_name"],
            charset="utf8mb4",
            connect_timeout=5
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM scam_logs WHERE scam_type=%s", (scam_type,))
            cnt = cur.fetchone()[0]
        conn.close()
        return cnt
    except Exception as e:
        logger.error(f"驗證 DB 時發生錯誤：{e}")
        return None

def cleanup_db(mysql_cfg, scam_type):
    try:
        conn = pymysql.connect(
            host=mysql_cfg["host"],
            port=int(mysql_cfg.get("port", 3306)),
            user=mysql_cfg["user"],
            password=mysql_cfg["password"],
            database=mysql_cfg["db_name"],
            charset="utf8mb4",
            connect_timeout=5
        )
        with conn.cursor() as cur:
            cur.execute("DELETE FROM scam_logs WHERE scam_type=%s", (scam_type,))
            deleted = cur.rowcount
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        logger.error(f"清除測試資料時發生錯誤：{e}")
        return None

def main(run_write: bool, do_cleanup: bool):
    mysql_cfg = config.get("mysql", {})
    if not mysql_cfg:
        print("config.mysql 未設定，請先檢查 config。")
        return

    if not mysql_cfg.get("enabled", True):
        print("MySQL 在設定中被停用（enabled=false），無法測試。")
        return

    test_text = f"測試寫入 {datetime.now().isoformat()}"
    print("使用 MySQLLogger 寫入測試紀錄...")
    if run_write:
        logger_obj = MySQLLogger()
        ok = logger_obj.log_scam(test_text, TEST_SCAM_TYPE, "測試縣市")
        print("MySQLLogger.log_scam 返回：", ok)
    else:
        print("跳過實際寫入（dry-run 模式）。若要寫入請使用 --run")

    time.sleep(0.5)
    cnt = verify_in_db(mysql_cfg, TEST_SCAM_TYPE)
    if cnt is None:
        print("無法驗證資料庫（連線或查詢失敗）。")
    else:
        print(f"資料庫中 scam_type={TEST_SCAM_TYPE} 的筆數：{cnt}")

    if do_cleanup:
        deleted = cleanup_db(mysql_cfg, TEST_SCAM_TYPE)
        if deleted is None:
            print("嘗試刪除測試資料時發生錯誤，請手動檢查資料庫。")
        else:
            print(f"已刪除 {deleted} 筆測試資料。")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="測試 MySQL 連線與寫入（使用專案 MySQLLogger）")
    p.add_argument("--run", action="store_true", help="實際執行寫入（預設為 dry-run）")
    p.add_argument("--cleanup", action="store_true", help="完成後刪除測試資料")
    args = p.parse_args()

    main(run_write=args.run, do_cleanup=args.cleanup)

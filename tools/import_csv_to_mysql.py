import csv
import argparse
from typing import Optional
from utils.log import logger
from config.paths import CSV_LOG_PATH
from storage.mysql_logger import MySQLLogger
import os

def import_csv_to_mysql(csv_path: Optional[str] = None, dry_run: bool = True, limit: Optional[int] = None):
    """
    從 CSV 匯入到 MySQL（使用專案內的 MySQLLogger）
    參數:
      csv_path: 指定 CSV 檔案路徑，若為 None 使用 config.paths.CSV_LOG_PATH
      dry_run: True 時僅列印統計，不執行寫入
      limit: 若指定，最多處理前 N 筆
    """
    csv_path = csv_path or CSV_LOG_PATH
    if not os.path.exists(csv_path):
        logger.error(f"CSV 檔案不存在：{csv_path}")
        return False

    logger.info(f"開始匯入 CSV（dry_run={dry_run}）：{csv_path}")
    mysql_logger = MySQLLogger()

    total = 0
    success = 0
    failed = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if limit and total >= limit:
                break
            total += 1

            timestamp = row.get("timestamp") or row.get("time") or ""
            county = row.get("county") or row.get("location") or "未知地區"
            user_input = row.get("user_input") or row.get("content") or ""
            scam_type = row.get("scam_type") or row.get("type") or "未分類"

            if not user_input:
                logger.warning(f"第 {total} 筆缺少 user_input，跳過")
                failed += 1
                continue

            if dry_run:
                # 只紀錄而不寫入
                logger.debug(f"[dry-run] {total}: {timestamp} | {county} | {scam_type}")
                success += 1
            else:
                try:
                    ok = mysql_logger.log_scam(user_input, scam_type, county)
                    if ok:
                        success += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"第 {total} 筆匯入失敗：{e}")
                    failed += 1

    logger.info(f"匯入完成（dry_run={dry_run}）：總筆數={total} 成功={success} 失敗={failed}")
    return True

def cli():
    parser = argparse.ArgumentParser(description="匯入 scam_logs CSV 到 MySQL（使用專案 MySQLLogger）")
    parser.add_argument("--csv", "-c", help="CSV 檔案路徑（預設使用 config.paths.CSV_LOG_PATH）")
    parser.add_argument("--run", action="store_true", help="執行實際寫入（預設為 dry-run）")
    parser.add_argument("--limit", "-n", type=int, help="最多處理前 N 筆")
    args = parser.parse_args()

    import_csv_to_mysql(csv_path=args.csv, dry_run=not args.run, limit=args.limit)

if __name__ == "__main__":
    cli()

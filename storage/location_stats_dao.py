import pymysql
from typing import Optional, Dict, List, Tuple
from datetime import date
from utils.log import logger
from config import config


class LocationStatsDAO:
    """
    提供縣市統計的資料庫存取：
    - live 計數（使用者互動即時累加）：table `location_stats_live`
    - 官方每日統計（165 官網匯入）：table `official_location_stats`
    查詢時可優先回傳最新官方統計，無官方資料時回退 live。
    """

    def __init__(self):
        self.db_conf = config.get("mysql", {})
        self.enabled = bool(self.db_conf.get("enabled", False))
        self._conn: Optional[pymysql.connections.Connection] = None

    # --- connection helpers ---
    def _connect(self) -> bool:
        if not self.enabled:
            return False
        try:
            host = self.db_conf["host"]
            port = int(self.db_conf.get("port", 3306))
            user = self.db_conf["user"]
            password = self.db_conf["password"]
            db_name = self.db_conf["db_name"]

            # 先確保資料庫存在
            tmp = pymysql.connect(host=host, port=port, user=user, password=password, charset="utf8mb4", connect_timeout=5)
            try:
                with tmp.cursor() as cur:
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
                tmp.commit()
            finally:
                try:
                    tmp.close()
                except Exception:
                    pass

            self._conn = pymysql.connect(host=host, port=port, user=user, password=password, database=db_name, charset="utf8mb4", connect_timeout=5)
            return True
        except Exception as e:
            logger.error(f"LocationStatsDAO 連線失敗：{e}")
            self._conn = None
            return False

    def _ensure_conn(self) -> bool:
        if self._conn:
            return True
        return self._connect()

    def close(self):
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        finally:
            self._conn = None

    # --- schema helpers ---
    def ensure_tables(self) -> bool:
        if not self._ensure_conn():
            return False
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS location_stats_live (
                        county VARCHAR(255) PRIMARY KEY,
                        cnt INT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS official_location_stats (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        stat_date DATE NOT NULL,
                        county VARCHAR(255) NOT NULL,
                        cnt INT NOT NULL,
                        UNIQUE KEY uk_date_county (stat_date, county)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"建立 location stats 表格失敗：{e}")
            try:
                self._conn.rollback()
            except Exception:
                pass
            return False

    # --- live counters ---
    def increment_live(self, county: str) -> bool:
        if not self._ensure_conn():
            return False
        if not self.ensure_tables():
            return False
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO location_stats_live (county, cnt) VALUES (%s, 1)
                    ON DUPLICATE KEY UPDATE cnt = cnt + 1;
                    """,
                    (county,)
                )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新 live 統計失敗：{e}")
            try:
                self._conn.rollback()
            except Exception:
                pass
            return False

    def get_live_counts(self) -> List[Tuple[str, int]]:
        if not self._ensure_conn():
            return []
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT county, cnt FROM location_stats_live ORDER BY cnt DESC;")
                rows = cur.fetchall()
            return [(r[0], int(r[1])) for r in rows]
        except Exception as e:
            logger.error(f"讀取 live 統計失敗：{e}")
            return []

    # --- official stats ---
    def upsert_official(self, stat_date: date, county: str, cnt: int) -> bool:
        if not self._ensure_conn():
            return False
        if not self.ensure_tables():
            return False
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO official_location_stats (stat_date, county, cnt)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE cnt = VALUES(cnt);
                    """,
                    (stat_date, county, cnt)
                )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"寫入官方統計失敗：{e}")
            try:
                self._conn.rollback()
            except Exception:
                pass
            return False

    def get_latest_official(self) -> List[Tuple[str, int]]:
        if not self._ensure_conn():
            return []
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT MAX(stat_date) FROM official_location_stats;")
                row = cur.fetchone()
                if not row or not row[0]:
                    return []
                latest = row[0]
                cur.execute(
                    "SELECT county, cnt FROM official_location_stats WHERE stat_date=%s ORDER BY cnt DESC;",
                    (latest,)
                )
                rows = cur.fetchall()
            return [(r[0], int(r[1])) for r in rows]
        except Exception as e:
            logger.error(f"讀取官方最新統計失敗：{e}")
            return []

    # --- combined ---
    def get_counts_prefer_official(self) -> List[Tuple[str, int]]:
        data = self.get_latest_official()
        if data:
            return data
        return self.get_live_counts()

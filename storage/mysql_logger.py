import pymysql
import socket
from datetime import datetime
from typing import Optional
from utils.log import logger
from config import config

class MySQLLogger:
    def __init__(self):
        """
        初始化MySQL日誌器（從配置中獲取DB連線資訊）
        """
        # 使用防呆的取法，避免 config 未設定 "mysql" 時拋錯
        self.db_config = config.get("mysql", {})
        self.conn: Optional[pymysql.connections.Connection] = None
        self.enabled = bool(self.db_config.get("enabled", True))

    def _port_open(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except Exception:
            return False

    def _connect(self) -> bool:
        """
        建立MySQL連線（內部方法，自動處理連線錯誤）
        
        Returns:
            bool: 連線成功返回True，失敗返回False
        """
        # 若未啟用，直接略過
        if not self.enabled:
            logger.info("MySQL 日誌已停用（config.mysql.enabled=false）")
            return False

        # 檢查基本設定
        # 必要欄位檢查（但允許使用預設 host/port/db_name）
        if not self.db_config.get("user") or not self.db_config.get("password"):
            logger.warning("MySQL 帳號或密碼未設定，略過 MySQL 紀錄。")
            return False

        try:
            host = self.db_config.get("host", "localhost")
            port = int(self.db_config.get("port", 3306))
            user = self.db_config.get("user")
            password = self.db_config.get("password")
            db_name = self.db_config.get("db_name") or self.db_config.get("database") or "scam_logs_db"

            # 先檢查埠是否可連線，避免長時間逾時與錯誤
            if not self._port_open(host, port):
                logger.warning(f"MySQL 服務無法連線（{host}:{port}），略過 MySQL 紀錄。")
                return False

            # 先嘗試無資料庫連線，用於自動建立資料庫
            tmp_conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                charset="utf8mb4",
                connect_timeout=2
            )
            try:
                with tmp_conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
                tmp_conn.commit()
                logger.info(f"確保資料庫已存在：{db_name}")
            finally:
                try:
                    tmp_conn.close()
                except Exception:
                    pass

            # 連線到目標資料庫
            self.conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db_name,
                charset="utf8mb4",
                connect_timeout=2
            )
            logger.info("成功連接MySQL資料庫")
            return True
        except Exception as e:
            # 連線被拒絕等預期情況，用 warning 降噪
            msg = str(e)
            if "Connection refused" in msg or "2003" in msg:
                logger.warning(f"MySQL連線失敗：{msg}")
            else:
                logger.error(f"MySQL連線失敗：{msg}")
            self.conn = None
            return False

    def _create_table(self) -> bool:
        """
        建立詐騙紀錄表（若不存在）
        
        Returns:
            bool: 建立成功返回True，失敗返回False
        """
        if not self.conn:
            logger.error("MySQL未連線，無法建立表格")
            return False
        
        try:
            with self.conn.cursor() as cursor:
                # 建立scam_logs表格（ID自增、時間戳、縣市、使用者輸入、詐騙類型）
                create_sql = """
                    CREATE TABLE IF NOT EXISTS scam_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp DATETIME NOT NULL,
                        county VARCHAR(255) NOT NULL,
                        user_input TEXT NOT NULL,
                        scam_type VARCHAR(255) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_sql)
            self.conn.commit()
            logger.info("成功建立/驗證scam_logs表格")
            return True
        except Exception as e:
            logger.error(f"建立MySQL表格失敗：{str(e)}")
            self.conn.rollback()
            return False

    def log_scam(
        self, 
        user_input: str, 
        scam_type: str, 
        county: str
    ) -> bool:
        """
        寫入詐騙紀錄到MySQL
        
        Args:
            user_input: 使用者輸入
            scam_type: 詐騙類型
            county: 縣市
        
        Returns:
            bool: 寫入成功返回True，失敗返回False
        """
        # 0. 未啟用或無法連線則靜默略過，不影響主流程
        if not self._connect():
            return False
        
        # 2. 建立表格（若不存在）
        if not self._create_table():
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
            return False
        
        try:
            # 3. 寫入紀錄
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self.conn.cursor() as cursor:
                insert_sql = """
                    INSERT INTO scam_logs (timestamp, county, user_input, scam_type)
                    VALUES (%s, %s, %s, %s);
                """
                cursor.execute(insert_sql, (timestamp, county, user_input, scam_type))
            self.conn.commit()
            logger.info(f"成功寫入MySQL日誌：{timestamp} | {county} | {scam_type}")
            return True
        
        except Exception as e:
            logger.error(f"寫入MySQL日誌失敗：{str(e)}")
            self.conn.rollback()
            return False
        
        finally:
            # 4. 無論成敗，關閉連線
            try:
                if self.conn:
                    self.conn.close()
                    logger.info("MySQL連線已關閉")
            except Exception:
                pass

    def init_db(self):
        """
        主動初始化資料庫與資料表，並回傳狀態。
        Returns:
            dict: {"enabled": bool, "connected": bool, "table_ready": bool, "error": str|None}
        """
        result = {"enabled": self.enabled, "connected": False, "table_ready": False, "error": None}
        if not self.enabled:
            return result
        try:
            if not self._connect():
                result["error"] = "connect failed"
                return result
            result["connected"] = True
            result["table_ready"] = bool(self._create_table())
            return result
        except Exception as e:
            result["error"] = str(e)
            return result
        finally:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
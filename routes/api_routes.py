from flask import Blueprint, request, jsonify
from typing import Dict, List
from datetime import datetime
from utils.log import logger
from utils.geo_utils import GeoReverser
from services.scam_classifier import ScamClassifier
from services.intent_classifier import IntentClassifier
from services.scam_related_check import ScamRelatedChecker
from services.reply_formatter import ReplyFormatter
from storage.memory_manager import MemoryManager
from storage.csv_logger import CSVLogger
from storage.mysql_logger import MySQLLogger
from config.paths import STORAGE_BASE_DIR
import storage.data_merger
from config import config
import pymysql
import os
import sqlite3
from typing import Dict, Any
from tools.import_csv_to_mysql import import_csv_to_mysql

# 建立Blueprint
api_bp = Blueprint("api", __name__)

# 初始化依賴模組（透過建構函式注入，便於測試）
geo_reverser = GeoReverser()
scam_classifier = ScamClassifier()
intent_classifier = IntentClassifier()
scam_related_checker = ScamRelatedChecker()
memory_manager = MemoryManager()
csv_logger = CSVLogger()
mysql_logger = MySQLLogger()

@api_bp.route("/ask", methods=["POST"])
def ask():
    """
    核心API路由：處理使用者查詢，返回分析結果
    請求參數：{"question": "使用者輸入", "latitude": 緯度, "longitude": 經度}
    響應格式：{"answer": "回覆內容", "scam_type": "詐騙類型", "intent": "意圖"}
    """
    try:
        # 1. 解析請求參數
        request_data = request.get_json()
        user_input = request_data.get("question", "").strip()
        session_id = request.remote_addr  # 以使用者IP作為session_id
        latitude = request_data.get("latitude")
        longitude = request_data.get("longitude")
        
        logger.info(f"收到使用者查詢：session_id={session_id} | input={user_input[:50]}...")
        
        # 驗證使用者輸入（不可為空）
        if not user_input:
            logger.warning("使用者輸入為空")
            return jsonify({"answer": "⚠️ 請輸入問題。"}), 400
        
        # 2. 初始化變數
        county = "未知地區"  # 預設縣市
        final_reply = ""
        scam_type = "無法分類"
        intent = "描述事件"
        
        # 3. 讀取使用者記憶
        user_memory = memory_manager.get_user_memory(session_id)
        history = user_memory["history"]  # 對話歷史（最近5條）
        
        # 4. 意圖判斷
        intent = intent_classifier.classify_intent(user_input, history)
        
        # 5. 處理不同意圖
        # 5.1 閒聊意圖：直接返回預設回覆
        if intent == "閒聊":
            final_reply = ReplyFormatter.get_default_reply(intent)
            return jsonify({
                "answer": final_reply,
                "scam_type": scam_type,
                "intent": intent
            })
        
        # 5.2 查詢記憶意圖：返回歷史記憶
        if intent == "查詢記憶":
            # 從記憶中提取上次分析結果
            last_memory = user_memory["memory"]
            last_scam_type = last_memory.get("lastScamType", "未知")
            last_summary = last_memory.get("lastEventSummary", "目前沒有摘要。")
            last_response = last_memory.get("lastResponse", "目前沒有記錄回覆內容。")
            
            # 根據使用者查詢關鍵字返回對應記憶
            if any(keyword in user_input for keyword in ["類型", "什麼詐騙", "哪種類型"]):
                final_reply = f"🧠 你上次的詐騙類型是「{last_scam_type}」。"
            elif any(keyword in user_input for keyword in ["機率", "風險", "可能性"]):
                # 與最新用語一致：不顯示百分比，改用風險等級
                final_reply = "📊 我記得你上次問到的案件，詐騙風險：高。"
            elif any(keyword in user_input for keyword in ["內容", "回覆", "分析"]):
                final_reply = f"📋 上次的回覆內容是：\n{last_response[:100]}..."
            elif any(keyword in user_input for keyword in ["摘要", "描述", "提到"]):
                final_reply = f"📌 你上次提到的內容是：{last_summary[:100]}..."
            else:
                final_reply = f"🧠 你上次的詐騙類型是「{last_scam_type}」，內容是：{last_summary[:50]}..."
            
            return jsonify({
                "answer": final_reply,
                "scam_type": last_scam_type,
                "intent": intent
            })
        
        # 5.3 非閒聊/查詢記憶：檢查是否與詐騙相關
        is_related = scam_related_checker.is_related(user_input, history)
        if not is_related:
            # 與 LINE 一致的保守策略：命中高信號關鍵詞則視為相關
            high_signal_keywords = [
                "銀行", "客服", "帳戶", "帳號", "轉帳", "匯款", "ATM", "異常交易", "驗證碼", "OTP",
                "檢察官", "法院", "拘票", "地檢署", "警察", "逮捕", "不配合", "保密"
            ]
            if any(kw in user_input for kw in high_signal_keywords):
                logger.warning("相關性檢查為 False，但命中高信號關鍵詞，改視為相關並繼續分析。")
            else:
                final_reply = "抱歉，您的問題似乎與詐騙無關，我目前專注於詐騙相關問題。"
                return jsonify({
                    "answer": final_reply,
                    "scam_type": scam_type,
                    "intent": intent
                })
        
        # 5.4 詐騙相關：呼叫Ollama獲取分析結果
        # 5.4.1 呼叫Ollama生成回答（詐騙分析）
        system_prompt = (
            "你是一位專業的詐騙分析助手。"
            "嚴格限制回答只針對詐騙相關問題，若使用者提問與詐騙無關，"
            "請禮貌回覆「抱歉，我只能回答詐騙相關問題」。"
            "回答內容請精準且聚焦於詐騙分析，不得漫談其他主題。"
            "請不要主動提及今天日期。"
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": f"請分析：{user_input}"})
        
        from utils.ollama_client import OllamaClient
        from config import config
        ollama_config = config["ollama"]
        ollama_client = OllamaClient(ollama_config["base_url"], ollama_config["web_model"])
        answer = ollama_client.send_chat_request(messages)
        
        # 處理Ollama呼叫失敗
        if not answer:
            answer = "對不起，我無法連接到伺服器，請稍後再試。"
        
        # 5.4.2 詐騙類型分類
        scam_type = scam_classifier.classify_scam_type(user_input, history)
        
        # 5.4.3 地理位置反查（若提供經緯度）
        if latitude and longitude:
            county = geo_reverser.reverse_geo(float(latitude), float(longitude))
            # 更新縣市統計
            geo_reverser.update_location_stats(county)
        
        # 5.4.4 寫入日誌（CSV + MySQL）
        csv_logger.log_scam(user_input, scam_type, county)
        mysql_logger.log_scam(user_input, scam_type, county)
        
        # 5.4.5 格式化回覆
        if ReplyFormatter.should_format(intent, scam_type, answer):
            final_reply = ReplyFormatter.format_reply(scam_type, answer)
        else:
            final_reply = answer
        
        # 5.4.6 更新使用者記憶（僅「描述事件」意圖更新記憶）
        if intent == "描述事件":
            # 更新對話歷史
            user_memory["history"].append({"role": "user", "content": user_input})
            user_memory["history"].append({"role": "assistant", "content": final_reply})
            # 更新業務記憶（上次詐騙類型、摘要、回覆）
            user_memory["memory"]["lastScamType"] = scam_type
            user_memory["memory"]["lastEventSummary"] = user_input
            user_memory["memory"]["lastResponse"] = final_reply
            # 寫回記憶檔
            memory_manager.update_user_memory(session_id, user_memory)
        
        # 6. 返回響應
        logger.info(f"處理完成：session_id={session_id} | scam_type={scam_type} | intent={intent}")
        return jsonify({
            "answer": final_reply,
            "scam_type": scam_type,
            "intent": intent
        })
    
    except Exception as e:
        logger.error(f"處理/ask請求失敗：{str(e)}", exc_info=True)
        return jsonify({"answer": "⚠️ 發生錯誤，請稍後再試。"}), 500

@api_bp.route("/memory", methods=["GET"])
def get_memory():
    """
    獲取使用者記憶路由
    響應格式：{"history": [], "memory": {}}
    """
    session_id = request.remote_addr
    user_memory = memory_manager.get_user_memory(session_id)
    return jsonify(user_memory)

@api_bp.route("/memory/clear", methods=["POST"])
def clear_memory():
    """
    清除使用者記憶路由
    響應格式：{"message": "操作結果"}
    """
    session_id = request.remote_addr
    success = memory_manager.clear_user_memory(session_id)
    if success:
        return jsonify({"message": "記憶已清除。"})
    else:
        return jsonify({"message": "清除記憶失敗，請稍後再試。"}), 500

@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    健康檢查路由（用於監控）
    響應格式：{"status": "healthy", "collection_ready": 是否準備就緒}
    """
    from src.data_loader import DataLoader
    from config import config
    
    # 檢查資料集合是否準備就緒（需嘗試載入）
    data_loader = DataLoader(config)
    try:
        data_loader.load_embeddings()
    except Exception:
        pass
    collection_ready = bool(data_loader.get_collection())
    
    return jsonify({
        "status": "healthy",
        "collection_ready": collection_ready,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@api_bp.route("/fraud-stats", methods=["GET"])
def fraud_stats():
    """
    提供前端儀表板使用的詐騙統計資料。
    來源：合併 CSV 日誌檔和即時資料（MySQL/JSON）。

    回傳格式：
    {
      "county_counts": [
        {"county": "台北市", "count": 12, "csv_count": 8, "live_count": 4, 
         "top5": [{"type": "假投資", "count": 5}, ...] },
        ...
      ],
      "top5": [ {"type": "假投資", "count": 20}, ... ],
      "summary": {...}
    }
    """
    from storage.data_merger import DataMerger
    from utils.log import logger

    try:
        # 使用新的資料合併器
        merger = DataMerger()
        detailed_stats = merger.get_detailed_fraud_stats()
        
        # 轉換資料格式以符合前端需求
        county_counts = []
        for county_data in detailed_stats['county_details']:
            county_counts.append({
                "county": county_data['county'],
                "count": county_data['total_count'],
                "csv_count": county_data['csv_count'],
                "live_count": county_data['live_count'],
                "top5": county_data['top5_scam_types']
            })
        
        # 全域 top5 詐騙類型
        top5_overall = detailed_stats['global_scam_types'][:5]
        
        return jsonify({
            "county_counts": county_counts,
            "top5": top5_overall,
            "summary": detailed_stats['summary']
        })
        
    except Exception as e:
        logger.error(f"獲取合併統計資料發生錯誤：{e}", exc_info=True)
        # 發生錯誤時回傳空資料
        return jsonify({
            "county_counts": [],
            "top5": [],
            "summary": {
                "total_counties": 0,
                "total_csv_records": 0,
                "total_live_records": 0,
                "grand_total": 0
            }
        })


@api_bp.route("/data-merger/status", methods=["GET"])
def data_merger_status():
    """
    獲取資料合併器的狀態資訊
    
    Returns:
        JSON: 包含各資料來源的狀態
    """
    from storage.data_merger import DataMerger
    from utils.log import logger
    
    try:
        merger = DataMerger()
        
        # 檢查各資料來源狀態
        csv_stats = merger.get_csv_statistics()
        live_stats = merger.get_live_statistics()
        
        return jsonify({
            "csv_source": {
                "available": bool(csv_stats['total_records'] > 0),
                "total_records": csv_stats['total_records'],
                "counties": len(csv_stats['county_stats']),
                "scam_types": len(csv_stats['scam_type_stats'])
            },
            "live_source": {
                "available": bool(live_stats['county_stats']),
                "source_type": live_stats['source'],
                "counties": len(live_stats['county_stats']),
                "total_count": sum(live_stats['county_stats'].values())
            },
            "merger_available": True
        })
        
    except Exception as e:
        logger.error(f"獲取資料合併器狀態失敗：{e}")
        return jsonify({
            "csv_source": {"available": False, "error": str(e)},
            "live_source": {"available": False, "error": str(e)},
            "merger_available": False
        }), 500


@api_bp.route("/data-merger/export", methods=["POST"])
def export_merged_data():
    """
    匯出合併後的資料為 JSON 檔案
    
    Returns:
        JSON: 匯出操作結果
    """
    from storage.data_merger import DataMerger
    from utils.log import logger
    import os
    
    try:
        merger = DataMerger()
        
        # 生成匯出檔案名稱（包含時間戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"merged_statistics_{timestamp}.json"
        output_path = os.path.join(STORAGE_BASE_DIR, output_filename)
        
        # 執行匯出
        success = merger.export_merged_data(output_path)
        
        if success:
            return jsonify({
                "success": True,
                "message": "資料匯出成功",
                "output_file": output_filename,
                "output_path": output_path
            })
        else:
            return jsonify({
                "success": False,
                "message": "資料匯出失敗"
            }), 500
            
    except Exception as e:
        logger.error(f"匯出合併資料失敗：{e}")
        return jsonify({
            "success": False,
            "message": f"匯出失敗：{str(e)}"
        }), 500


@api_bp.route("/data-merger/merge-summary", methods=["GET"])
def get_merger_summary():
    """
    獲取資料合併的摘要資訊
    
    Returns:
        JSON: 合併摘要
    """
    from storage.data_merger import DataMerger
    from utils.log import logger
    
    try:
        merger = DataMerger()
        merge_result = merger.merge_statistics()
        
        return jsonify({
            "merged_stats": merge_result['merged_county_stats'],
            "csv_contribution": merge_result['csv_stats'],
            "live_contribution": merge_result['live_stats'],
            "summary": {
                "total_counties": merge_result['total_counties'],
                "total_count": merge_result['total_count'],
                "sources_used": merge_result['sources_used']
            }
        })
        
    except Exception as e:
        logger.error(f"獲取合併摘要失敗：{e}")
        return jsonify({
            "error": f"獲取合併摘要失敗：{str(e)}"
        }), 500
    
@api_bp.route("/scam-types", methods=["GET"])
def scam_types():
    """
    僅回傳詐騙手法統計（來源：CSV + 即時資料合併）
    """
    try:
        from storage.data_merger import DataMerger
        merger = DataMerger()
        stats = merger.get_detailed_fraud_stats()
    except Exception as e:
        logger.error(f"獲取詐騙手法統計失敗：{e}", exc_info=True)
        return jsonify({
            "scam_types": [],
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": "無法取得詐騙手法統計"
        })
    
    if not stats:
        logger.warning("DataMerger 回傳空值，/scam-types 將提供空的詐騙手法列表。")
        scam_types = []
    else:
        scam_types = stats.get("global_scam_types", []) or []
    
    return jsonify({
        "scam_types": scam_types,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@api_bp.route("/articles/extract", methods=["POST"])
def extract_articles():
    """
    接收原始文章列表，擷取標題、發布單位、日期與內容連結。
    請求格式：
    {
        "items": [
            {"title": "...", "publisher": "...", "date": "...", "url": "..."},
            ...
        ]
    }
    回應格式：
    {
        "items": [...],
        "missing": [...],
        "requested": 10,
        "total": 8
    }
    """
    payload = request.get_json(silent=True) or {}
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return jsonify({"error": "請提供 items 陣列。"}), 400

    extracted: List[Dict[str, str]] = []
    missing: List[Dict[str, object]] = []

    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            missing.append({
                "index": idx,
                "missing_fields": ["title", "publisher", "published_at", "link"],
                "reason": "項目必須為物件"
            })
            continue

        normalized = {
            "title": item.get("title") or item.get("name"),
            "publisher": item.get("publisher") or item.get("agency"),
            "published_at": item.get("published_at") or item.get("date"),
            "link": item.get("link") or item.get("url") or item.get("id")
        }

        lacking = [field for field, value in normalized.items() if not value]
        if lacking:
            missing.append({"index": idx, "missing_fields": lacking})
            continue

        extracted.append(normalized)

    logger.info(f"/articles/extract 成功擷取 {len(extracted)} 筆資料（共 {len(raw_items)} 筆）。")

    return jsonify({
        "items": extracted,
        "missing": missing,
        "requested": len(raw_items),
        "total": len(extracted),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@api_bp.route("/db/init", methods=["GET"])
def db_init():
    """
    主動初始化資料庫與資料表，並回傳狀態。
    """
    try:
        result = mysql_logger.init_db()
        ok = result.get("enabled") and result.get("connected") and result.get("table_ready")
        return jsonify({"mysql": result}), (200 if ok else 503)
    except Exception as e:
        logger.error(f"DB 初始化檢查失敗：{e}")
        return jsonify({"mysql": {"enabled": mysql_logger.enabled, "error": str(e)}}), 500

@api_bp.route("/db/status", methods=["GET"])
def db_status():
    """
    檢查 MySQL 資料庫與 scam_logs 表是否存在，並回傳簡易統計。
    回傳 JSON 範例：
    {
      "connected": true,
      "database_exists": true,
      "table_exists": true,
      "record_count": 123,
      "error": null
    }
    """
    mysql_cfg = config.get("mysql", {})
    enabled = bool(mysql_cfg.get("enabled", True))
    host = mysql_cfg.get("host", "localhost")
    port = int(mysql_cfg.get("port", 3306))
    user = mysql_cfg.get("user")
    password = mysql_cfg.get("password")
    db_name = mysql_cfg.get("db_name") or mysql_cfg.get("database") or "scam_logs_db"

    if not enabled:
        return jsonify({
            "connected": False,
            "database_exists": False,
            "table_exists": False,
            "record_count": 0,
            "error": "MySQL 已在設定中被停用（mysql.enabled=false）"
        }), 503

    if not user or not password:
        return jsonify({
            "connected": False,
            "database_exists": False,
            "table_exists": False,
            "record_count": 0,
            "error": "MySQL 帳號或密碼未設定於 config"
        }), 500

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset="utf8mb4",
            connect_timeout=2,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        logger.warning(f"DB 連線失敗：{e}")
        return jsonify({
            "connected": False,
            "database_exists": False,
            "table_exists": False,
            "record_count": 0,
            "error": str(e)
        }), 503

    try:
        with conn.cursor() as cur:
            # 檢查資料庫是否存在
            cur.execute("SHOW DATABASES LIKE %s", (db_name,))
            db_exists = bool(cur.fetchone())

            table_exists = False
            record_count = None
            if db_exists:
                # 針對目標資料庫查表與筆數
                cur.execute(f"USE `{db_name}`;")
                cur.execute("SHOW TABLES LIKE 'scam_logs';")
                table_exists = bool(cur.fetchone())
                if table_exists:
                    try:
                        cur.execute("SELECT COUNT(*) AS cnt FROM scam_logs;")
                        row = cur.fetchone()
                        record_count = int(row["cnt"]) if row and "cnt" in row else 0
                    except Exception as e_count:
                        # 若 table 存在但查詢失敗，記錄警告但不中斷
                        logger.warning(f"查詢 scam_logs 筆數失敗：{e_count}")
                        record_count = None

        return jsonify({
            "connected": True,
            "database_exists": db_exists,
            "table_exists": table_exists,
            "record_count": record_count if record_count is not None else 0,
            "error": None
        }), 200

    except Exception as e:
        logger.error(f"檢查資料庫狀態發生錯誤：{e}", exc_info=True)
        return jsonify({
            "connected": True,
            "database_exists": False,
            "table_exists": False,
            "record_count": 0,
            "error": str(e)
        }), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

@api_bp.route("/admin/import-csv", methods=["POST"])
def admin_import_csv():
    """
    管理員 API：將 CSV 匯入 MySQL（使用 tools/import_csv_to_mysql.import_csv_to_mysql）
    POST JSON 可選參數：
      { "csv_path": "...", "run": true, "limit": 100 }
    若 run 為 true 則執行實際寫入，預設為 dry-run。
    """
    try:
        payload = request.get_json(silent=True) or {}
        csv_path = payload.get("csv_path")
        run_real = bool(payload.get("run", False))
        limit = payload.get("limit")
        ok = import_csv_to_mysql(csv_path=csv_path, dry_run=not run_real, limit=limit)
        return jsonify({"success": bool(ok), "dry_run": not run_real}), (200 if ok else 500)
    except Exception as e:
        logger.error(f"admin/import-csv 失敗：{e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
        

@api_bp.route("/admin/migrate-sqlite-to-mysql", methods=["POST"])
def admin_migrate_sqlite_to_mysql():
    """
    管理員 API：將本地 sqlite (scam_logs.db) 的資料搬到 MySQL。
    POST JSON 可選參數：
      { "sqlite_path": "...", "limit": 1000 }
    回傳插入成功/失敗筆數。
    """
    try:
        payload = request.get_json(silent=True) or {}
        sqlite_path = payload.get("sqlite_path") or os.path.join(STORAGE_BASE_DIR, "scam_logs.db")
        limit = payload.get("limit")

        if not os.path.exists(sqlite_path):
            return jsonify({"success": False, "error": f"sqlite file not found: {sqlite_path}"}), 400

        mysql_logger = MySQLLogger()
        # 嘗試初始化 DB/table（靜默處理）
        mysql_logger.init_db()

        # 讀 sqlite 資料
        conn = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        q = "SELECT timestamp, county, user_input, scam_type FROM scam_logs"
        if limit:
            q += f" LIMIT {int(limit)}"
        cur.execute(q)
        rows = cur.fetchall()
        conn.close()

        inserted = 0
        failed = 0
        for ts, county, user_input, scam_type in rows:
            try:
                ok = mysql_logger.log_scam(user_input or "", scam_type or "未分類", county or "未知地區")
                if ok:
                    inserted += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        return jsonify({"success": True, "inserted": inserted, "failed": failed, "rows": len(rows)}), 200
    except Exception as e:
        logger.error(f"admin/migrate-sqlite-to-mysql 失敗：{e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

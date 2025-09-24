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
    來源：CSV 日誌檔 `scam_logs.csv`（欄位：timestamp, county, user_input, scam_type）。

    回傳格式：
    {
      "county_counts": [
        {"county": "台北市", "count": 12, "top5": [{"type": "假投資", "count": 5}, ...] },
        ...
      ],
      "top5": [ {"type": "假投資", "count": 20}, ... ]
    }
    """
    import csv
    from collections import defaultdict, Counter
    from utils.log import logger
    from config.paths import CSV_LOG_PATH

    csv_path = CSV_LOG_PATH
    county_map = defaultdict(lambda: {"count": 0, "top5": Counter()})
    total_counter = Counter()

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                county = (row.get("county") or "未知地區").strip()
                scam_type = (row.get("scam_type") or "未分類").strip()
                county_map[county]["count"] += 1
                county_map[county]["top5"][scam_type] += 1
                total_counter[scam_type] += 1
    except FileNotFoundError:
        logger.warning(f"找不到CSV檔案：{csv_path}，回傳空統計。")
    except Exception as e:
        logger.error(f"讀取CSV統計發生錯誤：{e}", exc_info=True)

    def to_top5_list(counter: Counter):
        return [
            {"type": scam_type, "count": count}
            for scam_type, count in counter.most_common(5)
        ]

    county_count_list = [
        {
            "county": county,
            "count": data["count"],
            "top5": to_top5_list(data["top5"]) \
                if isinstance(data["top5"], Counter) else data["top5"],
        }
        for county, data in county_map.items()
    ]

    top5_overall = to_top5_list(total_counter)

    return jsonify({
        "county_counts": county_count_list,
        "top5": top5_overall
    })
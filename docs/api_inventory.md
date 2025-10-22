# API Inventory（自動產生） — main-165project

## 目的
列出專案內與 API、路由、以及資料庫互動相關的檔案與端點，方便整合並移除舊檔案。

---

## 主要路由檔案
- routes/api_routes.py
  - 主要 API 集中處
  - 端點：
    - POST /api/ask
    - GET /api/memory
    - POST /api/memory/clear
    - GET /api/health
    - GET /api/fraud-stats
    - GET /api/data-merger/status
    - POST /api/data-merger/export
    - GET /api/data-merger/merge-summary
    - GET /api/scam-types
    - POST /api/articles/extract
    - GET /api/db/init
    - GET /api/db/status
  - 與資料庫相關：
    - 呼叫 storage.mysql_logger.MySQLLogger.log_scam 寫入
    - 使用 storage.data_merger.DataMerger 讀取合併統計（間接存取 MySQL via LocationStatsDAO）
  - 其他注意：包含 Ollama client 呼叫、geo 反查、記憶管理等。

## 與 DB / 日誌 相關的 storage 模組
- storage/mysql_logger.py
  - 自動 CREATE DATABASE / CREATE TABLE（寫入時懶初始化）
  - 提供 log_scam() 與新增的 init_db()
  - 連線參數來源：config["mysql"]
- storage/csv_logger.py
  - 寫入 CSV 檔作為離線日誌（備份）
- storage/data_merger.py
  - 合併 CSV 與即時資料來源（會呼叫 LocationStatsDAO）
  - 方法：get_csv_statistics(), get_live_statistics(), get_detailed_fraud_stats(), export_merged_data(), sync_csv_to_live()
- storage/location_stats_dao.py
  - 與 MySQL 的即時縣市統計互動（如 get_live_counts(), increment_live()）
- storage/memory_manager.py
  - 使用者 session 記憶讀寫（history, memory）

## services（業務邏輯）
- services/scam_classifier.py：詐騙類型分類（會 log）
- services/intent_classifier.py：意圖分類（會呼叫 Ollama）
- services/scam_related_check.py：詐騙相關性檢查（關鍵詞/heuristic）
- services/reply_formatter.py：回覆格式化

## utils
- utils/ollama_client.py：呼叫 Ollama（外部 LLM）
- utils/geo_utils.py：經緯度到縣市反查
- utils/log.py：logging 設定與 logger
- src/data_loader.py：向量嵌入與 chromadb client（health 檢查會呼叫）

## tools / 舊腳本（可考慮刪除或整合）
- tools/import_csv_to_mysql.py：CSV → MySQL 匯入工具（保留為工具或移到 tools/）
- tools/test_mysql_connection.py：MySQL 測試腳本（保留）
- dashboard_app.py：舊版獨立 dashboard server（建議刪除或移入 docs/ 作備份）
- 其他臨時獨立 Flask app（若存在）請搜尋 run.py 或其他獨立 app 檔案。

---

## 要整合的項目（優先順序）
1. 保留 routes/api_routes.py 作為單一 API surface；把散落在 tools 或獨立 app 的 route 移回此檔。  
2. 將資料庫初始化（init_db）與健康檢查（db/status, data-merger/status）統一呼叫 storage/mysql_logger.py / storage/data_merger.py。  
3. 把所有寫入日誌行為統一：CSV 寫入可維持備份，但 MySQL 寫入應由 MySQLLogger 控制。  
4. 把舊 dashboard_app.py、獨立 flask server、或重複的 endpoint 檔案刪除（或移到 `archive/`）。

---

## 建議刪除 / 移動清單（請先備份）
建議先把下面檔案移到 `archive/` 或以 git branch 備份，再刪除：
- main-165project/dashboard_app.py  <-- 已停用（建議刪除）
- 任意專案根目錄中的獨立 Flask app（例如發現 run.py 中的獨立 server 副本，若已整合則刪除）
- 舊版儲存或測試腳本（若功能已整合至 tools/）

Git 刪除範例（確認無誤後執行）：
```bash
git mv dashboard_app.py archive/dashboard_app.py
git commit -m "chore: archive old dashboard_app"
# 或直接刪除
git rm dashboard_app.py
git commit -m "chore: remove deprecated dashboard_app"
```

---

## 驗證 / 測試清單（整合後必做）
1. 啟動 MySQL，執行 GET /api/db/init，應回傳 connected/table_ready = true。  
2. 呼叫 POST /api/ask（測試輸入） -> 檢查 MySQL 是否新增紀錄（或 CSV）。  
3. 呼叫 GET /api/data-merger/status 與 /api/fraud-stats，確認來源與數值。  
4. 執行 tools/test_mysql_connection.py 驗證連線。  
5. 若使用 chromadb：備份並測試 src/data_loader.py 的 load_embeddings 行為。

---

## 下一步建議（執行順序）
1. 建立分支 `feature/api-consolidation`。  
2. 備份 dashboard_app.py 與任何獨立 server 到 archive/。  
3. 在 routes/api_routes.py 確認所有 endpoint 與工具重複項目移除或合併。  
4. 執行 DB 初始化 API `/api/db/init`，確定成功。  
5. 移除 archive 中的檔案並合併回主分支。

---

## Quick grep（可在專案根目錄執行）
列出含 "route" / "Blueprint" / "api" 的檔案：
```bash
grep -R --line-number -E "Blueprint|@api_bp|/api/" .
```

列出直接使用 pymysql 的檔案：
```bash
grep -R --line-number -E "pymysql|MySQL" .
```

---

資料已整理完成，若要我：
- 幫你把舊檔移到 archive/（我可以修改 repo），或
- 直接在 repo 中刪除指定檔案（提供清單），
請回覆要執行的動作與要刪除/保留的檔案清單。

# 165 Scam Analyzer (Flask + LINE Bot)

一個以 Flask 建構的詐騙分析服務，提供：
- Web 介面（首頁/聊天/儀表板）
- REST API（核心 `/api/ask`、統計 `/api/fraud-stats`、健康檢查 `/api/health`）
- LINE Webhook（`/line/webhook` 與 `/webhook` 別名）

系統整合 Ollama 以進行詐騙分類與回覆生成，並以 ChromaDB 做向量檢索。MySQL 為可選的記錄後端，預設關閉。

## 目錄結構

```
main-165project/
├─ run.py                # 啟動入口
├─ requirements.txt      # 依賴清單
├─ .env                  # 環境變數（不進版控）
├─ config/
│  ├─ config.yaml        # 應用設定（Server/Ollama/Chroma/Embedding/MySQL）
│  └─ paths.py           # 路徑常數集中管理
├─ app/
│  └─ __init__.py        # Flask App Factory、CORS、Blueprint 註冊
├─ routes/
│  ├─ web_routes.py      # Web 頁面（/、/home、/chat、/dashboard）
│  ├─ api_routes.py      # REST API（/api/*）
│  └─ line_webhook_routes.py # LINE Webhook（/line/webhook 與 /webhook）
├─ services/
│  ├─ intent_classifier.py     # 意圖判斷
│  ├─ scam_classifier.py       # 詐騙類型分類
│  ├─ scam_related_check.py    # 詐騙相關性檢查（含啟發式 + 嚴格 LLM 解析）
│  └─ reply_formatter.py       # 回覆格式化
├─ src/
│  ├─ data_loader.py     # 載入/建立 Chroma 向量庫
│  ├─ query_engine.py     # 以 embedding 查詢向量庫
│  ├─ response_generator.py # 以 Ollama 生成回覆（支援 brief/detailed）
│  └─ line_handler.py     # LINE 事件處理（含 CA 憑證設定與 fallback）
├─ storage/
│  ├─ csv_logger.py      # CSV 紀錄（供儀表板/統計使用）
│  ├─ mysql_logger.py    # MySQL 可選紀錄（可停用）
│  └─ data/              # 向量庫與原始資料（embeddings.pkl、chroma_db/ 等）
└─ static/               # 前端靜態檔
```

## 安裝與啟動

1) 建立與啟用虛擬環境（macOS, zsh）
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) 設定環境變數 `.env`
```
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_CHANNEL_SECRET=your_line_secret
# 可選：LINE Webhook 驗證時用的用戶 ID（LINE Console 點「Verify」來測試）
LINE_VERIFY_USER_ID=
# 可選：若你要啟用 MySQL 紀錄
MYSQL_USER=scam
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
```

3) 調整 `config/config.yaml`
- 伺服器：預設 `0.0.0.0:8091`
- Ollama：
  - `ollama.base_url`（全域）
  - `ollama.web.model`、`ollama.line.model`（生成模型，預設 `mistral`）
  - `ollama.line.embedding_model`（向量化模型，建議 `nomic-embed-text`）
- Chroma：`chroma.path` 使用 `config/paths.py` 中的 `CHROMA_DB_DIR`
- MySQL：`mysql.enabled` 預設 `false`，若要啟用請設定帳密與資料庫

4) 啟動 Flask
```
python3 run.py
```
- Web 首頁：http://localhost:8091
- Chat 頁面：/chat（前端呼叫 `/api/ask`）
- 儀表板：/dashboard（前端呼叫 `/api/fraud-stats`）

## LINE Webhook 設定

- ngrok 對外映射：
```
ngrok http 8091
```
- 將 LINE Webhook URL 設為：
  - `https://<你的-ngrok-domain>/line/webhook`（或 `/webhook` 別名）
- 驗證與 SSL：
  - 內建以 `certifi` 設定 CA 憑證，避免 SSL 驗證失敗
  - 在驗證（Verify）請求中，如 `LINE_VERIFY_USER_ID` 匹配，會直接回傳 `OK`

## Ollama 與模型

本專案透過 Ollama 進行 embedding 與生成：
```
# 啟動 Ollama 服務（另開終端）
ollama serve
# 下載模型
ollama pull mistral
ollama pull nomic-embed-text
```
- `QueryEngine` 會依 `config.ollama.line.base_url` 設定 `OLLAMA_HOST`
- 生成時使用 `ollama.line.model`；向量化使用 `ollama.line.embedding_model`

## 向量庫與資料載入

- `src/data_loader.py` 會嘗試讀取下列檔案，建立/更新 Chroma collection：
  - `storage/data/embeddings_2.pkl`（優先）
  - `storage/data/embeddings.pkl`
- 支援格式：
  - `list[tuple[str, list[float]]]`
  - `list[dict{document|text|content, embedding|embeddings|vector}]`
  - `dict{documents: list[str], embeddings: list[list[float]]}`
- 若均不存在或格式錯誤，會建立空 collection（服務仍可啟動）。

## 服務邏輯重點

- Scam 相關性檢查（`services/scam_related_check.py`）
  - 先用啟發式（高信號關鍵詞、長數字樣式）過濾
  - 再呼叫 LLM，且以嚴格的「是/否」解析；無法判斷時保守視為相關
- 查無向量文件的 LINE 回覆
  - `line_handler` 已加後備策略：查不到資料時，直接以使用者敘述做「簡短分析」回覆，不再回錯誤訊息
- CSV 與 MySQL 記錄
  - CSV：預設開啟，用於儀表板統計（位置 `config.paths.CSV_LOG_PATH`）
  - MySQL：可選，`config.mysql.enabled=false` 時跳過，不影響主流程

## API 速查

- `POST /api/ask`
  - Body: `{ "question": "...", "latitude": 25.04, "longitude": 121.56 }`
  - 回傳：`{ "answer": "...", "scam_type": "...", "intent": "..." }`
- `GET /api/fraud-stats`
  - 回傳：各縣市計數與類型 Top5、整體 Top5
- `GET /api/health`
  - 回傳：`{"status":"healthy","collection_ready": true/false, ...}`

## 常見問題（FAQ）

- 前端 404：
  - 請確認前端呼叫的是 `/api/ask`（已修正 `static/js/chat.js` 與 `static/script.js`）
- LINE 回覆「無法找到相關資料」：
  - 已加後備生成。若要提高命中率，請補齊 embeddings 或提供語料，我們可加一鍵匯入腳本。
- MySQL 連不上：
  - 預設 `config.mysql.enabled=false`，若要啟用，請先啟動 MySQL、建立帳密與資料庫，並填入 `.env`/`config.yaml`。
- Ollama 連線錯誤：
  - 確認 `ollama serve` 有啟動、`base_url` 正確、模型已 `pull`。

## 開發小抄

- 重新載入向量庫：重啟服務即可（`data_loader` 啟動時會載入）
- 自測詐騙相關性：
```
python3 -m services._selftest_scam_check
```
- 檔案忽略：`main-165project/.gitignore` 已排除 `.env`、logs、embeddings、Chroma DB、CSV/JSON 等自動產生物件

## 授權

本專案內含示例代碼與設定，請依實際需求調整與加固安全性（如憑證管理、存取控制）。
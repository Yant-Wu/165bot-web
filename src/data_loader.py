import os
import pickle
import chromadb
import logging
import yaml
from typing import Any, List, Tuple, Optional
from config.paths import CHROMA_DB_DIR, EMBEDDINGS_PATH, EMBEDDINGS_V2_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, config):
        self.config = config
        # 延後初始化，避免在 import 階段就因為 sysdb 損毀而崩潰
        self.client = None
        self.collection = None
        self.max_batch_size = 5461  # ChromaDB 最大批次限制

    def _init_chroma_client(self, persist_dir: str = None, in_memory: bool = False):
        """
        初始化 chromadb client（可選 persist 或 in-memory）
        """
        persist_dir = persist_dir or CHROMA_DB_DIR
        self.persist_directory = persist_dir
        try:
            if in_memory and hasattr(chromadb, "EphemeralClient"):
                self.client = chromadb.EphemeralClient()
                logger.info("已啟動 chromadb EphemeralClient（記憶體模式）")
            else:
                self.client = chromadb.PersistentClient(path=persist_dir)
                logger.info(f"已啟動 chromadb PersistentClient：{persist_dir}")
        except Exception as e:
            logger.warning(f"初始化 chromadb client 失敗（in_memory={in_memory}）：{e}")
            self.client = None

    def _reset_chroma_store(self):
        """
        嘗試清理 chroma persist 目錄中常見的損壞檔案（sqlite / json），以便重建。
        注意：此動作會清除 chromadb 的 metadata，請務必先備份。
        """
        persist_dir = getattr(self, "persist_directory", CHROMA_DB_DIR)
        if not os.path.exists(persist_dir):
            logger.info(f"chromadb persist 目錄不存在，無需清理：{persist_dir}")
            return
        logger.warning(f"嘗試清理 chromadb persist 目錄：{persist_dir}（請確認已備份）")
        try:
            for fname in os.listdir(persist_dir):
                fpath = os.path.join(persist_dir, fname)
                # 常見需刪除的：sqlite 檔、損壞的 json、lock 檔
                if fname.endswith(".sqlite") or fname.endswith(".sqlite-shm") or fname.endswith(".sqlite-wal") or fname.endswith(".db") or fname.endswith(".lock") or fname.endswith(".json"):
                    try:
                        os.remove(fpath)
                        logger.info(f"已刪除：{fpath}")
                    except Exception as e:
                        logger.warning(f"刪除檔案失敗：{fpath} -> {e}")
        except Exception as e:
            logger.error(f"清理 chromadb persist 目錄時發生錯誤：{e}")

    def load_embeddings(self):
        """
        載入 embeddings 並建立或取得 collection（包含容錯處理）
        """
        def _try_load_pickle(path: str) -> Optional[Any]:
            try:
                with open(path, "rb") as f:
                    return pickle.load(f)
            except FileNotFoundError:
                return None
            except Exception as e:
                logger.warning(f"讀取嵌入檔失敗：{path} | {e}")
                return None

        def _normalize_data(data: Any) -> List[Tuple[str, List[float]]]:
            # 支援多種結構：
            # 1) List[Tuple[doc, emb]]
            # 2) List[Dict{"document": str, "embedding": List[float]}]
            # 3) Dict{"documents": List[str], "embeddings": List[List[float]]}
            if isinstance(data, list):
                if not data:
                    return []
                first = data[0]
                if isinstance(first, tuple) and len(first) == 2:
                    return [(str(doc), emb) for doc, emb in data]
                if isinstance(first, dict):
                    # 寬鬆支持常見鍵名
                    doc_keys = ["document", "doc", "text", "content"]
                    emb_keys = ["embedding", "embeddings", "vector", "embedding_vector", "emb"]
                    dk = next((k for k in doc_keys if k in first), None)
                    ek = next((k for k in emb_keys if k in first), None)
                    if dk and ek:
                        norm = []
                        for item in data:
                            doc_val = str(item.get(dk, ""))
                            emb_val = item.get(ek)
                            # 轉 list，避免 numpy array 影響
                            try:
                                if hasattr(emb_val, "tolist"):
                                    emb_val = emb_val.tolist()
                            except Exception:
                                pass
                            norm.append((doc_val, emb_val))
                        return norm
            if isinstance(data, dict) and "documents" in data and "embeddings" in data:
                docs = data.get("documents") or []
                embs = data.get("embeddings") or []
                return list(zip([str(d) for d in docs], embs))
            # 不支援的格式
            raise ValueError("未知的嵌入資料格式，請確認檔案內容。")

        primary = EMBEDDINGS_V2_PATH if os.path.exists(EMBEDDINGS_V2_PATH) else EMBEDDINGS_PATH
        backup = EMBEDDINGS_PATH if primary == EMBEDDINGS_V2_PATH else EMBEDDINGS_V2_PATH
        candidates = []
        # 去重且保序
        for p in [primary, backup]:
            if p and p not in candidates:
                candidates.append(p)

        embedded_data = None
        used_path = None
        for path in candidates:
            data = _try_load_pickle(path)
            if data is None:
                continue
            try:
                embedded_data = _normalize_data(data)
                used_path = path
                break
            except Exception as e:
                logger.warning(f"解析嵌入資料結構失敗：{path} | {e}")
                continue

        # 初始化 chroma client（延後到這裡）
        if self.client is None:
            self._init_chroma_client(in_memory=False)
            if self.client is None:
                # 無法初始化 persistent，直接嘗試記憶體模式
                self._init_chroma_client(in_memory=True)

        # 建立/取得 collection，含自動修復與 fallback
        def _ensure_collection() -> bool:
            if not self.client:
                return False
            try:
                self.collection = self.client.get_or_create_collection(name="demodocs")
                return True
            except KeyError as ke:
                # 常見：sysdb 配置 JSON 損毀導致 '_type' KeyError
                logger.error(f"取得 collection 時發生 KeyError：{ke}，嘗試清理並重建", exc_info=True)
                self._reset_chroma_store()
                self._init_chroma_client(in_memory=False)
                try:
                    if self.client:
                        self.collection = self.client.get_or_create_collection(name="demodocs")
                        return True
                except Exception as e2:
                    logger.error(f"清理後仍無法建立 collection：{e2}", exc_info=True)
                    return False
            except Exception as e:
                logger.warning(f"建立/取得 collection 發生例外：{e}", exc_info=True)
                return False

        if not _ensure_collection():
            # 改用記憶體模式作為最後手段
            self._init_chroma_client(in_memory=True)
            if not _ensure_collection():
                logger.error("無法建立任何 chroma collection，放棄載入嵌入。")
                self.collection = None
                return False

        if embedded_data is None:
            # 全部失敗：建立空 collection，避免啟動失敗
            if not any(os.path.exists(p) for p in candidates):
                logger.warning(f"找不到任何嵌入檔：{candidates}，建立空的collection")
            else:
                logger.warning(f"所有候選嵌入檔無法讀取或格式不符：{candidates}，建立空的collection")
            return True

        # 寫入 ChromaDB
        batch_size = min(self.config["embedding"]["batch_size"], self.max_batch_size)
        total = len(embedded_data)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = embedded_data[start:end]
            ids = [str(i + start) for i in range(len(batch))]
            documents = [doc for doc, _ in batch]
            embeddings = [emb for _, emb in batch]
            logger.info(f"載入批次：{start} 到 {end}，大小：{len(batch)}")
            self.collection.upsert(ids=ids, embeddings=embeddings, documents=documents)

        logger.info(f"嵌入資料載入完成（來源：{used_path}，總數：{total}）")
        return True

    def get_collection(self):
        return self.collection

if __name__ == "__main__":
    with open("../config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    loader = DataLoader(config)
    loader.load_embeddings()

# 說明：
# - 在 health_check 中被呼叫：data_loader.load_embeddings(), get_collection()
# - 檢查點：
#   - 是否連接到向量資料庫或其他資料源（Milvus / Faiss / Pinecone / DB）
#   - load_embeddings 是否會存取磁碟或遠端 DB
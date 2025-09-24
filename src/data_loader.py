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
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.collection = None
        self.max_batch_size = 5461  # ChromaDB 最大批次限制

    def load_embeddings(self):
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

        if embedded_data is None:
            # 全部失敗：建立空 collection，避免啟動失敗
            if not any(os.path.exists(p) for p in candidates):
                logger.warning(f"找不到任何嵌入檔：{candidates}，建立空的collection")
            else:
                logger.warning(f"所有候選嵌入檔無法讀取或格式不符：{candidates}，建立空的collection")
            self.collection = self.client.get_or_create_collection(name="demodocs")
            return True

        # 寫入 ChromaDB
        self.collection = self.client.get_or_create_collection(name="demodocs")
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
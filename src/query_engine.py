import ollama
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class QueryEngine:
    def __init__(self, collection, config):
        self.collection = collection
        self.config = config

    def query(self, user_input):
        if not self.collection:
            logger.warning("資料庫尚未初始化")
            return None

        try:
            base_url = (self.config or {}).get("base_url")
            if base_url:
                os.environ.setdefault("OLLAMA_HOST", base_url)

            model = (
                (self.config or {}).get("embedding_model")
                or (self.config or {}).get("model")
            )
            if not model:
                raise KeyError("embedding model is not configured (expected 'embedding_model' or 'model')")

            response = ollama.embeddings(
                prompt=user_input,
                model=model
            )
            query_embedding = response["embedding"]

            results = self.collection.query(query_embeddings=[query_embedding], n_results=3)
            documents = results.get("documents", [[]])[0] if results else []
            # 過濾空白/None 文件
            documents = [d for d in documents if isinstance(d, str) and d.strip()]
            
            if not documents:
                logger.warning("未找到相關資料")
                return None
            
            return "\n\n".join(documents)
        except Exception as e:
            logger.error(f"查詢時發生錯誤：{e}")
            return None
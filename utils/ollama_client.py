import requests
from typing import List, Dict, Optional
from utils.log import logger

class OllamaClient:
    def __init__(self, base_url: str, default_model: str):
        """
        初始化Ollama API用戶端
        
        Args:
            base_url: Ollama伺服器URL（如：http://localhost:11434）
            default_model: 預設使用的模型（如：mistral）
        """
        self.base_url = base_url.rstrip("/")  # 確保URL結尾無斜線
        self.default_model = default_model
        self.chat_endpoint = f"{self.base_url}/api/chat"  # 聊天API端點

    def send_chat_request(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None, 
        stream: bool = False
    ) -> Optional[str]:
        """
        傳送請求到Ollama Chat API
        
        Args:
            messages: 對話歷史（含system prompt、user input）
            model: 自訂模型（預設使用初始化時的default_model）
            stream: 是否開啟串流模式（此專案用於非串流）
        
        Returns:
            Optional[str]: Ollama回應內容（失敗時回傳None）
        """
        try:
            # 組合請求參數
            request_data = {
                "model": model or self.default_model,
                "messages": messages,
                "stream": stream
            }
            
            # 發送POST請求
            response = requests.post(
                url=self.chat_endpoint,
                json=request_data,
                timeout=10  # 設定超時時間，避免阻塞
            )
            response.raise_for_status()  # 若狀態碼非2xx，拋出異常
            
            # 解析回應（非串流模式）
            return response.json()["message"]["content"].strip()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API請求失敗：{str(e)}")
            return None
        except KeyError as e:
            logger.error(f"Ollama回應格式錯誤（缺少欄位）：{str(e)}")
            return None
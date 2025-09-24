import os
import json
from typing import Dict, List, Optional
from utils.log import logger

class MemoryManager:
    def __init__(self, memory_path: str = "memory.json"):
        """
        初始化使用者記憶管理器（儲存到JSON檔）
        
        Args:
            memory_path: 記憶檔案路徑
        """
        self.memory_path = memory_path
        # 初始化記憶檔（若不存在則建立空檔案）
        if not os.path.exists(self.memory_path):
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            logger.info(f"建立新的使用者記憶檔：{self.memory_path}")

    def get_user_memory(self, session_id: str) -> Dict:
        """
        獲取特定使用者的記憶（以session_id區分使用者，這裡用IP作為session_id）
        
        Args:
            session_id: 使用者識別ID（request.remote_addr）
        
        Returns:
            Dict: 使用者記憶（格式：{"history": [], "memory": {}}）
        """
        try:
            # 讀取所有使用者記憶
            with open(self.memory_path, "r", encoding="utf-8") as f:
                all_memory = json.load(f)
            
            # 若使用者無記憶，返回預設結構
            user_memory = all_memory.get(session_id, {
                "history": [],  # 對話歷史
                "memory": {}    # 業務記憶（如上次詐騙類型）
            })
            
            # 限制歷史長度（只保留最近5條，避免記憶過大）
            user_memory["history"] = user_memory["history"][-5:]
            logger.info(f"成功讀取使用者({session_id})記憶")
            return user_memory
        
        except Exception as e:
            logger.error(f"讀取使用者({session_id})記憶失敗：{str(e)}")
            # 失敗時返回空記憶
            return {"history": [], "memory": {}}

    def update_user_memory(
        self, 
        session_id: str, 
        user_memory: Dict
    ) -> bool:
        """
        更新使用者記憶
        
        Args:
            session_id: 使用者識別ID
            user_memory: 最新的使用者記憶
        
        Returns:
            bool: 更新成功返回True，失敗返回False
        """
        try:
            # 讀取所有記憶
            with open(self.memory_path, "r", encoding="utf-8") as f:
                all_memory = json.load(f)
            
            # 更新當前使用者記憶
            all_memory[session_id] = user_memory
            
            # 寫回檔案
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(all_memory, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功更新使用者({session_id})記憶")
            return True
        
        except Exception as e:
            logger.error(f"更新使用者({session_id})記憶失敗：{str(e)}")
            return False

    def clear_user_memory(self, session_id: str) -> bool:
        """
        清除特定使用者的記憶
        
        Args:
            session_id: 使用者識別ID
        
        Returns:
            bool: 清除成功返回True，失敗返回False
        """
        try:
            with open(self.memory_path, "r", encoding="utf-8") as f:
                all_memory = json.load(f)
            
            # 刪除使用者記憶（若存在）
            if session_id in all_memory:
                del all_memory[session_id]
                with open(self.memory_path, "w", encoding="utf-8") as f:
                    json.dump(all_memory, f, ensure_ascii=False, indent=2)
                logger.info(f"成功清除使用者({session_id})記憶")
                return True
            else:
                logger.warning(f"使用者({session_id})無記憶可清除")
                return True
        
        except Exception as e:
            logger.error(f"清除使用者({session_id})記憶失敗：{str(e)}")
            return False
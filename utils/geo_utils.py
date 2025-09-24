import requests
from typing import Optional
from utils.log import logger

class GeoReverser:
    def __init__(self, user_agent: str = "ScamAnalyzer/1.0 (admin@example.com)"):
        """
        初始化地理位置反查工具（基於OpenStreetMap Nominatim API）
        
        Args:
            user_agent: API請求的User-Agent（Nominatim要求必須提供）
        """
        self.base_url = "https://nominatim.openstreetmap.org/reverse"
        self.headers = {"User-Agent": user_agent}

    def reverse_geo(
        self, 
        latitude: float, 
        longitude: float
    ) -> str:
        """
        透過經緯度反查縣市名稱
        
        Args:
            latitude: 緯度
            longitude: 經度
        
        Returns:
            str: 縣市名稱（如：台北市），失敗時回傳「未知地區」
        """
        try:
            # 組合API參數
            params = {
                "format": "json",
                "lat": latitude,
                "lon": longitude,
                "accept-language": "zh-TW"  # 要求回傳中文結果
            }
            
            # 發送反查請求
            response = requests.get(
                url=self.base_url,
                params=params,
                headers=self.headers,
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            
            # 提取縣市（優先取county，無則取city）
            address = result.get("address", {})
            county = address.get("county") or address.get("city")
            
            if not county:
                logger.warning(f"經緯度({latitude},{longitude})無法解析縣市")
                return "未知地區"
            
            # 統一「臺」為「台」（如：臺北市 → 台北市）
            return county.strip().replace("臺", "台")
        
        except Exception as e:
            logger.error(f"地理位置反查失敗：{str(e)}")
            return "未知地區"

    def update_location_stats(
        self, 
        county: str, 
        stats_path: str = None
    ) -> None:
        """
        更新縣市查詢次數統計（儲存到JSON檔）
        
        Args:
            county: 縣市名稱
            stats_path: 統計檔案路徑
        """
        import json
        import os
        from config.paths import STORAGE_BASE_DIR

        if not stats_path:
            stats_path = os.path.join(STORAGE_BASE_DIR, "location_stats.json")

        # 讀取現有統計
        stats = {}
        if os.path.exists(stats_path):
            with open(stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
        
        # 更新次數
        stats[county] = stats.get(county, 0) + 1
        logger.info(f"縣市統計更新：{county}（次數：{stats[county]}）")
        
        # 寫回檔案
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
"""
資料合併模組 - 將 CSV 歷史資料與即時資料進行合併
功能包括：
1. 從 CSV 檔案讀取和統計歷史資料
2. 與即時資料（MySQL/JSON）合併
3. 提供統一的查詢介面
4. 避免重複計算和資料不一致問題
"""

import csv
import json
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
from collections import defaultdict, Counter
from utils.log import logger
from config.paths import CSV_LOG_PATH, STORAGE_BASE_DIR
from storage.location_stats_dao import LocationStatsDAO


class DataMerger:
    """資料合併器 - 合併 CSV 歷史資料與即時資料"""
    
    def __init__(self, csv_path: str = CSV_LOG_PATH):
        """
        初始化資料合併器
        
        Args:
            csv_path: CSV 檔案路徑
        """
        self.csv_path = csv_path
        self.location_dao = LocationStatsDAO()
        self.json_stats_path = os.path.join(STORAGE_BASE_DIR, "location_stats.json")
    
    def get_csv_statistics(self) -> Dict:
        """
        從 CSV 檔案讀取並統計歷史資料
        
        Returns:
            Dict: 包含縣市統計、詐騙類型統計等資訊
        """
        county_stats = defaultdict(int)
        scam_type_stats = defaultdict(int)
        county_scam_map = defaultdict(lambda: defaultdict(int))
        total_records = 0
        
        try:
            if not os.path.exists(self.csv_path):
                logger.warning(f"CSV 檔案不存在：{self.csv_path}")
                return self._empty_stats()
            
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    county = (row.get('county') or '未知地區').strip()
                    scam_type = (row.get('scam_type') or '未分類').strip()
                    
                    # 統計計數
                    county_stats[county] += 1
                    scam_type_stats[scam_type] += 1
                    county_scam_map[county][scam_type] += 1
                    total_records += 1
            
            logger.info(f"成功讀取 CSV 資料：共 {total_records} 筆記錄")
            
        except Exception as e:
            logger.error(f"讀取 CSV 檔案失敗：{e}")
            return self._empty_stats()
        
        return {
            'county_stats': dict(county_stats),
            'scam_type_stats': dict(scam_type_stats),
            'county_scam_map': {k: dict(v) for k, v in county_scam_map.items()},
            'total_records': total_records
        }
    
    def get_live_statistics(self) -> Dict:
        """
        獲取即時統計資料（優先 MySQL，失敗則使用 JSON）
        
        Returns:
            Dict: 即時統計資料
        """
        try:
            # 嘗試從 MySQL 獲取資料
            if self.location_dao.enabled:
                live_data = self.location_dao.get_live_counts()
                if live_data:
                    county_stats = {county: count for county, count in live_data}
                    logger.info(f"成功從 MySQL 獲取即時資料：{len(county_stats)} 個縣市")
                    return {
                        'county_stats': county_stats,
                        'source': 'mysql'
                    }
        except Exception as e:
            logger.warning(f"從 MySQL 獲取即時資料失敗：{e}")
        
        # 嘗試從 JSON 獲取資料
        try:
            if os.path.exists(self.json_stats_path):
                with open(self.json_stats_path, 'r', encoding='utf-8') as f:
                    county_stats = json.load(f)
                logger.info(f"成功從 JSON 獲取即時資料：{len(county_stats)} 個縣市")
                return {
                    'county_stats': county_stats,
                    'source': 'json'
                }
        except Exception as e:
            logger.warning(f"從 JSON 獲取即時資料失敗：{e}")
        
        return {
            'county_stats': {},
            'source': 'none'
        }
    
    def merge_statistics(self, include_csv: bool = True, include_live: bool = True) -> Dict:
        """
        合併 CSV 和即時統計資料
        
        Args:
            include_csv: 是否包含 CSV 資料
            include_live: 是否包含即時資料
        
        Returns:
            Dict: 合併後的統計資料
        """
        merged_county_stats = defaultdict(int)
        csv_stats = {}
        live_stats = {}
        
        # 獲取 CSV 資料
        if include_csv:
            csv_data = self.get_csv_statistics()
            csv_stats = csv_data['county_stats']
            for county, count in csv_stats.items():
                merged_county_stats[county] += count
        
        # 獲取即時資料
        if include_live:
            live_data = self.get_live_statistics()
            live_stats = live_data['county_stats']
            for county, count in live_stats.items():
                merged_county_stats[county] += count
        
        # 轉換結果
        result = {
            'merged_county_stats': dict(merged_county_stats),
            'csv_stats': csv_stats,
            'live_stats': live_stats,
            'total_counties': len(merged_county_stats),
            'total_count': sum(merged_county_stats.values()),
            'sources_used': []
        }
        
        if include_csv and csv_stats:
            result['sources_used'].append('csv')
        if include_live and live_stats:
            result['sources_used'].append('live')
        
        logger.info(f"資料合併完成：{result['total_counties']} 個縣市，總計 {result['total_count']} 筆")
        return result
    
    def get_detailed_fraud_stats(self) -> Dict:
        """
        獲取詳細的詐騙統計資料（主要基於 CSV 資料）
        
        Returns:
            Dict: 詳細統計資料，包含縣市和詐騙類型的交叉分析
        """
        csv_data = self.get_csv_statistics()
        live_data = self.get_live_statistics()
        
        # 準備回傳資料
        county_detailed = []
        
        # 處理每個縣市的詳細資料
        for county, csv_count in csv_data['county_stats'].items():
            live_count = live_data['county_stats'].get(county, 0)
            
            # 取得該縣市的詐騙類型統計
            scam_types = csv_data['county_scam_map'].get(county, {})
            top5_scam_types = [
                {"type": scam_type, "count": count}
                for scam_type, count in Counter(scam_types).most_common(5)
            ]
            
            county_detailed.append({
                "county": county,
                "csv_count": csv_count,
                "live_count": live_count,
                "total_count": csv_count + live_count,
                "top5_scam_types": top5_scam_types
            })
        
        # 處理只在即時資料中出現的縣市
        for county, live_count in live_data['county_stats'].items():
            if county not in csv_data['county_stats']:
                county_detailed.append({
                    "county": county,
                    "csv_count": 0,
                    "live_count": live_count,
                    "total_count": live_count,
                    "top5_scam_types": []
                })
        
        # 按總數排序
        county_detailed.sort(key=lambda x: x['total_count'], reverse=True)
        
        # 全域詐騙類型統計
        global_scam_types = [
            {"type": scam_type, "count": count}
            for scam_type, count in Counter(csv_data['scam_type_stats']).most_common()
        ]
        
        return {
            "county_details": county_detailed,
            "global_scam_types": global_scam_types,
            "summary": {
                "total_counties": len(county_detailed),
                "total_csv_records": csv_data['total_records'],
                "total_live_records": sum(live_data['county_stats'].values()),
                "grand_total": csv_data['total_records'] + sum(live_data['county_stats'].values())
            }
        }
    
    def sync_csv_to_live(self, start_date: Optional[str] = None) -> bool:
        """
        將 CSV 資料同步到即時統計資料庫
        注意：這個功能需要謹慎使用，避免重複計算
        
        Args:
            start_date: 開始同步的日期（格式：YYYY-MM-DD），None 表示同步全部
        
        Returns:
            bool: 同步是否成功
        """
        try:
            if not self.location_dao.enabled:
                logger.warning("MySQL 未啟用，無法同步資料")
                return False
            
            csv_stats = self.get_csv_statistics()
            
            # 將 CSV 統計的縣市資料寫入資料庫
            success_count = 0
            total_count = len(csv_stats['county_stats'])
            
            for county, count in csv_stats['county_stats'].items():
                # 這裡我們使用 increment_live 來增加計數
                # 但要注意避免重複計算的問題
                try:
                    # 由於我們要同步歷史資料，這裡需要特殊處理
                    # 建議在實際使用前先清空 live 表格或使用特殊的同步方法
                    if self.location_dao.increment_live(county):
                        success_count += 1
                except Exception as e:
                    logger.warning(f"同步縣市 {county} 失敗：{e}")
            
            logger.info(f"資料同步完成：{success_count}/{total_count} 個縣市同步成功")
            return success_count == total_count
            
        except Exception as e:
            logger.error(f"資料同步失敗：{e}")
            return False
        finally:
            self.location_dao.close()
    
    def _empty_stats(self) -> Dict:
        """回傳空的統計資料結構"""
        return {
            'county_stats': {},
            'scam_type_stats': {},
            'county_scam_map': {},
            'total_records': 0
        }
    
    def export_merged_data(self, output_path: str = None) -> bool:
        """
        將合併後的資料匯出為 JSON 檔案
        
        Args:
            output_path: 輸出檔案路徑
        
        Returns:
            bool: 匯出是否成功
        """
        try:
            if not output_path:
                output_path = os.path.join(STORAGE_BASE_DIR, "merged_statistics.json")
            
            merged_data = self.get_detailed_fraud_stats()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"合併資料已匯出至：{output_path}")
            return True
            
        except Exception as e:
            logger.error(f"匯出合併資料失敗：{e}")
            return False


# 便利函數
def get_merged_fraud_statistics() -> Dict:
    """
    便利函數：獲取合併後的詐騙統計資料
    
    Returns:
        Dict: 合併統計資料
    """
    merger = DataMerger()
    return merger.get_detailed_fraud_stats()


def merge_and_export(output_path: str = None) -> bool:
    """
    便利函數：合併資料並匯出
    
    Args:
        output_path: 輸出檔案路徑
    
    Returns:
        bool: 操作是否成功
    """
    merger = DataMerger()
    return merger.export_merged_data(output_path)
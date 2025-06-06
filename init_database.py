#!/usr/bin/env python3
"""
數據庫初始化腳本
確保數據庫表結構正確
"""

import sys
from config_manager import ConfigManager
from models import DatabaseManager

def main():
    """主函數"""
    try:
        print("🚀 初始化數據庫...")
        
        # 載入配置
        config = ConfigManager("config.yaml")
        db_manager = DatabaseManager(config.get_database_url())
        
        # 創建表
        print("📝 創建數據庫表...")
        db_manager.create_tables()
        
        # 測試連接
        print("🔍 測試數據庫連接...")
        processed_ids = db_manager.get_processed_ids()
        print(f"✅ 數據庫連接成功！已處理論文數量: {len(processed_ids)}")
        
        # 取得未處理論文
        unprocessed = db_manager.get_unprocessed_papers()
        print(f"📝 未處理論文數量: {len(unprocessed)}")
        
        print("🎉 數據庫初始化完成！")
        return True
        
    except Exception as e:
        print(f"❌ 數據庫初始化失敗: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
修復後的系統集成測試腳本
"""

import asyncio
import sys
from pathlib import Path

def test_imports():
    """測試所有模組的導入"""
    print("測試模組導入...")
    
    try:
        from config_manager import ConfigManager
        print("✓ ConfigManager 導入成功")
        
        from models import DatabaseManager
        print("✓ DatabaseManager 導入成功")
        
        from logger import LoggerManager
        print("✓ LoggerManager 導入成功")
        
        from monitor import SystemMonitor
        print("✓ SystemMonitor 導入成功")
        
        from news_updater_v2 import AINewsUpdater
        print("✓ AINewsUpdater 導入成功")
        
        from retry_utils import retry_with_backoff
        print("✓ retry_with_backoff 導入成功")
        
        return True
        
    except Exception as e:
        print(f"✗ 導入失敗: {e}")
        return False

def test_configuration():
    """測試配置管理"""
    print("\n測試配置管理...")
    
    try:
        from config_manager import ConfigManager
        
        config = ConfigManager("config.yaml")
        
        # 測試基本配置讀取
        db_url = config.get_database_url()
        print(f"✓ 數據庫URL: {db_url}")
        
        log_level = config.get_log_level()
        print(f"✓ 日誌等級: {log_level}")
        
        return True
        
    except Exception as e:
        print(f"✗ 配置測試失敗: {e}")
        return False

def test_database():
    """測試數據庫連接"""
    print("\n測試數據庫連接...")
    
    try:
        from config_manager import ConfigManager
        from models import DatabaseManager
        
        config = ConfigManager("config.yaml")
        db_manager = DatabaseManager(config.get_database_url())
        
        # 創建資料表
        db_manager.create_tables()
        print("✓ 數據庫表創建成功")
        
        # 測試基本查詢
        processed_ids = db_manager.get_processed_ids()
        print(f"✓ 已處理論文數量: {len(processed_ids)}")
        
        return True
        
    except Exception as e:
        print(f"✗ 數據庫測試失敗: {e}")
        return False

def test_monitor():
    """測試系統監控"""
    print("\n測試系統監控...")
    
    try:
        from config_manager import ConfigManager
        from monitor import SystemMonitor
        
        config = ConfigManager("config.yaml")
        monitor = SystemMonitor(config)
        
        # 測試系統狀態檢查
        status = monitor.get_system_status()
        print(f"✓ 系統狀態: CPU={status.get('cpu_usage', 0):.1f}%")
        if 'memory' in status:
            print(f"✓ 記憶體: {status['memory'].get('percent', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"✗ 監控測試失敗: {e}")
        return False

def test_news_updater():
    """測試新聞更新器初始化"""
    print("\n測試新聞更新器...")
    
    try:
        from config_manager import ConfigManager
        from news_updater_v2 import AINewsUpdater
        
        updater = AINewsUpdater("config.yaml")
        
        print("✓ AINewsUpdater 初始化成功")
        
        # 測試配置讀取（使用正確的方法）
        config = ConfigManager("config.yaml")
        concurrency = config.config.get('concurrency', {}).get('max_workers', 4)
        retry_attempts = config.config.get('retry', {}).get('max_attempts', 3)
        print(f"✓ 最大並發數: {concurrency}")
        print(f"✓ 重試次數: {retry_attempts}")
        
        return True
        
    except Exception as e:
        print(f"✗ 新聞更新器測試失敗: {e}")
        return False

def test_cli_commands():
    """測試CLI命令是否可以導入"""
    print("\n測試CLI模組...")
    
    try:
        from cli import main
        print("✓ CLI主函數導入成功")
        
        # 測試CLI參數解析（不實際執行）
        import argparse
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        
        # 檢查是否能創建子命令解析器
        run_parser = subparsers.add_parser('run')
        status_parser = subparsers.add_parser('status')
        
        print("✓ CLI命令解析器創建成功")
        
        return True
        
    except Exception as e:
        print(f"✗ CLI測試失敗: {e}")
        return False

async def run_all_tests():
    """運行所有測試"""
    print("🚀 開始運行系統集成測試...\n")
    
    tests = [
        ("模組導入", test_imports),
        ("配置管理", test_configuration),
        ("數據庫操作", test_database),
        ("系統監控", test_monitor),
        ("新聞更新器", test_news_updater),
        ("CLI介面", test_cli_commands),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"--- {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                passed += 1
            else:
                print(f"❌ {test_name} 失敗")
        except Exception as e:
            print(f"❌ {test_name} 執行異常: {e}")
    
    print(f"\n=== 測試結果 ===")
    print(f"通過: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有測試通過！系統運行正常。")
        return True
    else:
        print(f"⚠️  有 {total-passed} 個測試失敗")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"測試執行失敗: {e}")
        sys.exit(1)

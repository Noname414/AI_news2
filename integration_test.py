#!/usr/bin/env python3
"""
系統集成測試腳本
測試整個重構後的 AI 新聞更新系統
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from config_manager import ConfigManager
from models import DatabaseManager
from news_updater_v2 import AINewsUpdater
from monitor import SystemMonitor
from logger import LoggerManager

class SystemIntegrationTest:
    """系統集成測試"""
    
    def __init__(self):
        self.temp_dir = None
        self.test_config_path = None
        self.original_config = None
        self.logger = None
    
    async def setup_test_environment(self):
        """設置測試環境"""
        # 創建臨時目錄
        self.temp_dir = Path(tempfile.mkdtemp())
        logger.info(f"創建測試環境: {self.temp_dir}")
        
        # 創建測試配置
        test_config = {
            'database': {
                'url': f'sqlite:///{self.temp_dir}/test_news.db',
                'echo': False
            },
            'files': {
                'audio_dir': str(self.temp_dir / 'audios'),
                'log_dir': str(self.temp_dir / 'logs')
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_handler': {
                    'enabled': True,
                    'max_bytes': 1048576,
                    'backup_count': 3
                }
            },
            'apis': {
                'gemini': {
                    'model': 'gemini-pro',
                    'rate_limit': 10,
                    'timeout': 30
                },
                'arxiv': {
                    'max_results': 5,  # 測試時只獲取少量數據
                    'query': 'cat:cs.AI',
                    'sort_by': 'submittedDate',
                    'sort_order': 'descending'
                }
            },
            'concurrency': {
                'max_workers': 2,
                'semaphore_limit': 2
            },
            'retry': {
                'max_attempts': 2,
                'initial_delay': 1,
                'max_delay': 5,
                'exponential_base': 2
            }
        }
        
        # 寫入測試配置文件
        self.test_config_path = self.temp_dir / 'test_config.yaml'
        import yaml
        with open(self.test_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 創建必要的目錄
        (self.temp_dir / 'audios').mkdir(exist_ok=True)
        (self.temp_dir / 'logs').mkdir(exist_ok=True)
    
    async def cleanup_test_environment(self):
        """清理測試環境"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info("清理測試環境完成")
    
    async def test_configuration_loading(self):
        """測試配置加載"""
        logger.info("測試配置加載...")
        
        try:
            config = ConfigManager(str(self.test_config_path))
            
            # 驗證配置
            assert config.get_database_url().startswith('sqlite:///')
            assert config.get('apis.gemini.model') == 'gemini-pro'
            assert config.get('concurrency.max_workers') == 2
            
            logger.info("✓ 配置加載測試通過")
            return True
            
        except Exception as e:
            logger.error(f"✗ 配置加載測試失敗: {e}")
            return False
    
    async def test_database_operations(self):
        """測試數據庫操作"""
        logger.info("測試數據庫操作...")
        
        try:
            config = ConfigManager(str(self.test_config_path))
            db_manager = DatabaseManager(config.get_database_url())
            
            # 初始化數據庫
            await db_manager.init_database()
            
            # 測試基本操作
            paper_id = "test_paper_123"
            
            # 檢查論文是否存在（應該不存在）
            existing = await db_manager.get_paper_by_id(paper_id)
            assert existing is None
            
            # 檢查是否已處理（應該未處理）
            is_processed = await db_manager.is_paper_processed(paper_id)
            assert not is_processed
            
            # 標記為已處理
            await db_manager.mark_paper_processed(paper_id)
            
            # 再次檢查（應該已處理）
            is_processed = await db_manager.is_paper_processed(paper_id)
            assert is_processed
            
            # 獲取統計信息
            stats = await db_manager.get_statistics()
            assert 'total_papers' in stats
            
            logger.info("✓ 數據庫操作測試通過")
            return True
            
        except Exception as e:
            logger.error(f"✗ 數據庫操作測試失敗: {e}")
            return False
    
    async def test_system_monitor(self):
        """測試系統監控"""
        logger.info("測試系統監控...")
        
        try:
            config = ConfigManager(str(self.test_config_path))
            monitor = SystemMonitor(config)
            
            # 測試健康檢查
            health = monitor.check_health()
            assert 'cpu_usage' in health
            assert 'memory_usage' in health
            assert 'disk_usage' in health
            
            # 測試數據庫統計（需要先初始化數據庫）
            db_manager = DatabaseManager(config.get_database_url())
            await db_manager.init_database()
            
            db_stats = await monitor.get_database_stats()
            assert 'total_papers' in db_stats
            
            logger.info("✓ 系統監控測試通過")
            return True
            
        except Exception as e:
            logger.error(f"✗ 系統監控測試失敗: {e}")
            return False
    
    async def test_news_updater_initialization(self):
        """測試新聞更新器初始化"""
        logger.info("測試新聞更新器初始化...")
        
        try:
            config = ConfigManager(str(self.test_config_path))
            updater = AINewsUpdater(config)
            
            # 檢查組件是否正確初始化
            assert updater.config is not None
            assert updater.db_manager is not None
            assert updater.logger is not None
            
            logger.info("✓ 新聞更新器初始化測試通過")
            return True
            
        except Exception as e:
            logger.error(f"✗ 新聞更新器初始化測試失敗: {e}")
            return False
    
    async def test_mock_paper_processing(self):
        """測試模擬論文處理（避免實際 API 調用）"""
        logger.info("測試模擬論文處理...")
        
        try:
            config = ConfigManager(str(self.test_config_path))
            updater = AINewsUpdater(config)
            
            # 模擬論文數據
            mock_paper = {
                'id': '2024.01.001',
                'title': 'Test Paper Title',
                'summary': 'This is a test paper abstract.',
                'authors': ['Author One', 'Author Two'],
                'published': '2024-01-01',
                'pdf_url': 'https://arxiv.org/pdf/2024.01.001.pdf',
                'categories': ['cs.AI']
            }
            
            # 模擬 API 調用
            with patch.object(updater, '_translate_text', new_callable=AsyncMock) as mock_translate:
                with patch.object(updater, '_generate_audio', new_callable=AsyncMock) as mock_audio:
                    mock_translate.return_value = "測試翻譯結果"
                    mock_audio.return_value = str(self.temp_dir / 'audios' / 'test.mp3')
                    
                    # 處理論文
                    result = await updater._process_paper(mock_paper)
                    
                    # 驗證結果
                    assert result is not None
                    assert 'translated_title' in result
                    assert 'translated_abstract' in result
                    assert 'audio_path' in result
            
            logger.info("✓ 模擬論文處理測試通過")
            return True
            
        except Exception as e:
            logger.error(f"✗ 模擬論文處理測試失敗: {e}")
            return False
    
    async def run_all_tests(self):
        """運行所有測試"""
        logger.info("開始運行系統集成測試...")
        
        try:
            await self.setup_test_environment()
            
            tests = [
                ('配置加載', self.test_configuration_loading),
                ('數據庫操作', self.test_database_operations),
                ('系統監控', self.test_system_monitor),
                ('新聞更新器初始化', self.test_news_updater_initialization),
                ('模擬論文處理', self.test_mock_paper_processing),
            ]
            
            passed = 0
            total = len(tests)
            
            for test_name, test_func in tests:
                logger.info(f"\n--- 執行測試: {test_name} ---")
                if await test_func():
                    passed += 1
                else:
                    logger.error(f"測試失敗: {test_name}")
            
            # 輸出測試結果
            logger.info(f"\n=== 測試結果 ===")
            logger.info(f"通過: {passed}/{total}")
            logger.info(f"成功率: {passed/total*100:.1f}%")
            
            if passed == total:
                logger.info("🎉 所有測試通過！系統運行正常。")
                return True
            else:
                logger.warning(f"⚠️  有 {total-passed} 個測試失敗")
                return False
                
        except Exception as e:
            logger.error(f"測試執行失敗: {e}")
            return False
        
        finally:
            await self.cleanup_test_environment()

async def main():
    """主函數"""
    tester = SystemIntegrationTest()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

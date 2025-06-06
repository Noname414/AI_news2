"""
AI 新聞更新器測試
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from config_manager import ConfigManager
from models import DatabaseManager
from news_updater_v2 import AINewsUpdater

class TestConfigManager:
    """測試設定管理器"""
    
    def test_load_config_success(self):
        """測試成功載入設定檔"""
        config = ConfigManager("config.yaml")
        assert config.get_app_name() == "AI News Updater"
        assert config.get_app_version() == "2.0.0"
    
    def test_load_config_file_not_found(self):
        """測試設定檔不存在的情況"""
        with pytest.raises(FileNotFoundError):
            ConfigManager("non_existent_config.yaml")
    
    def test_get_arxiv_queries(self):
        """測試取得 arXiv 查詢詞"""
        config = ConfigManager("config.yaml")
        queries = config.get_arxiv_queries()
        assert isinstance(queries, list)
        assert len(queries) > 0

class TestDatabaseManager:
    """測試資料庫管理器"""
    
    @pytest.fixture
    def db_manager(self):
        """建立測試用的資料庫管理器"""
        # 使用記憶體資料庫進行測試
        return DatabaseManager("sqlite:///:memory:")
    
    def test_create_tables(self, db_manager):
        """測試建立資料表"""
        db_manager.create_tables()
        # 如果沒有例外就表示成功
        assert True
    
    def test_save_paper(self, db_manager):
        """測試儲存論文"""
        db_manager.create_tables()
        
        paper_data = {
            "id": "test123",
            "query": "AI",
            "url": "http://example.com",
            "title": "Test Paper",
            "summary": "Test summary",
            "authors": ["Author 1", "Author 2"],
            "published_date": "2023-01-01"
        }
        
        result = db_manager.save_paper(paper_data)
        assert result == True
    
    def test_get_processed_ids(self, db_manager):
        """測試取得已處理的 ID"""
        db_manager.create_tables()
        
        # 先儲存一篇論文
        paper_data = {
            "id": "test123",
            "query": "AI",
            "url": "http://example.com",
            "title": "Test Paper",
            "summary": "Test summary",
            "authors": ["Author 1"],
            "published_date": "2023-01-01",
            "processed": True
        }
        db_manager.save_paper(paper_data)
        
        processed_ids = db_manager.get_processed_ids()
        assert "test123" in processed_ids

class TestAINewsUpdater:
    """測試 AI 新聞更新器"""
    
    @pytest.fixture
    def mock_config(self):
        """模擬設定"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
app:
  name: "Test AI News Updater"
  version: "2.0.0"

database:
  url: "sqlite:///:memory:"
  
paths:
  audio_dir: "test_audios"
  log_dir: "test_logs"
  news_jsonl: "test_news.jsonl"

arxiv:
  queries:
    - "AI"
  max_results_per_query: 1
  max_results_total: 10
  sort_by: "SubmittedDate"

gemini:
  model: "gemini-2.0-flash-001"
  temperature: 0.7
  max_output_tokens: 2000
  max_retries: 3
  retry_delay: 1.0

tts:
  language: "zh-tw"
  slow: false
  max_retries: 3

prompts:
  translation: |
    Test prompt: {title} {summary}

concurrency:
  max_workers: 2
  enable_async: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_handler: false
  console_handler: true
  max_bytes: 10485760
  backup_count: 5
"""
            f.write(config_content)
            f.flush()
            return f.name
    
    @pytest.fixture
    def updater(self, mock_config):
        """建立測試用的更新器"""
        # 設定環境變數
        os.environ["GEMINI_API_KEY"] = "test_key"
        
        with patch('news_updater_v2.genai.Client'):
            updater = AINewsUpdater(mock_config)
            return updater
    
    def test_init(self, updater):
        """測試初始化"""
        assert updater.config is not None
        assert updater.logger is not None
        assert updater.db is not None
    
    @patch('news_updater_v2.arxiv.Client')
    def test_fetch_papers_for_query(self, mock_arxiv_client, updater):
        """測試抓取特定查詢的論文"""
        # 模擬 arXiv 回應
        mock_result = Mock()
        mock_result.get_short_id.return_value = "test123"
        mock_result.entry_id = "http://example.com"
        mock_result.title = "Test Paper"
        mock_result.summary = "Test summary"
        mock_result.authors = [Mock(name="Author 1")]
        mock_result.published.strftime.return_value = "2023-01-01"
        
        mock_client = Mock()
        mock_client.results.return_value = [mock_result]
        mock_arxiv_client.return_value = mock_client
        
        papers = updater.fetch_papers_for_query("AI")
        assert len(papers) == 1
        assert papers[0]["id"] == "test123"
    
    @pytest.mark.asyncio
    async def test_translate_paper(self, updater):
        """測試翻譯論文"""
        # 模擬 Gemini 回應
        mock_response = Mock()
        mock_response.parsed = Mock()
        mock_response.parsed.title_zh = "測試標題"
        mock_response.parsed.summary_zh = "測試摘要"
        mock_response.parsed.applications = ["應用1", "應用2", "應用3"]
        mock_response.parsed.pitch = "測試推銷"
        
        with patch.object(updater.gemini_client.models, 'generate_content', return_value=mock_response):
            result = await updater.translate_paper("test123", "Test Title", "Test Summary")
            
            assert result["title_zh"] == "測試標題"
            assert result["summary_zh"] == "測試摘要"
            assert len(result["applications"]) == 3
    
    def test_create_audio_content(self, updater):
        """測試建立音訊內容"""
        translation = {
            "title_zh": "測試標題",
            "summary_zh": "測試摘要",
            "applications": ["應用1", "應用2", "應用3"],
            "pitch": "測試推銷"
        }
        
        content = updater._create_audio_content(translation)
        assert "測試標題" in content
        assert "測試摘要" in content
        assert "應用1" in content
        assert "測試推銷" in content

@pytest.mark.asyncio
async def test_rate_limiter():
    """測試速率限制器"""
    from retry_utils import RateLimiter
    
    rate_limiter = RateLimiter(max_calls=2, time_window=1.0)
    
    # 前兩次調用應該立即通過
    await rate_limiter.acquire()
    await rate_limiter.acquire()
    
    # 第三次調用應該被限制
    import time
    start_time = time.time()
    await rate_limiter.acquire()
    end_time = time.time()
    
    # 應該等待了一些時間
    assert end_time - start_time > 0.5

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

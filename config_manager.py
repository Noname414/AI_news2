"""
設定檔管理器
"""
import os
import yaml
from typing import Dict, Any, List
from pathlib import Path

class ConfigManager:
    """設定檔管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config = None
        self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """載入設定檔"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            self._validate_config()
            self._create_directories()
            return self._config
        except FileNotFoundError:
            raise FileNotFoundError(f"設定檔不存在: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"設定檔格式錯誤: {e}")
    
    def _validate_config(self):
        """驗證設定檔必要欄位"""
        required_sections = ['app', 'database', 'paths', 'arxiv', 'gemini']
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"設定檔缺少必要區段: {section}")
                
        # 驗證 API 金鑰
        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("環境變數 GEMINI_API_KEY 未設定")
    
    def _create_directories(self):
        """建立必要的目錄"""
        directories = [
            self.get_audio_dir(),
            self.get_log_dir()
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    @property
    def config(self) -> Dict[str, Any]:
        """取得設定"""
        return self._config
    
    # App 設定
    def get_app_name(self) -> str:
        return self._config['app']['name']
    
    def get_app_version(self) -> str:
        return self._config['app']['version']
    
    # 資料庫設定
    def get_database_url(self) -> str:
        return self._config['database']['url']
    
    # 路徑設定
    def get_audio_dir(self) -> str:
        return self._config['paths']['audio_dir']
    
    def get_log_dir(self) -> str:
        return self._config['paths']['log_dir']
    
    def get_news_jsonl_path(self) -> str:
        return self._config['paths']['news_jsonl']
    
    # arXiv 設定
    def get_arxiv_queries(self) -> List[str]:
        return self._config['arxiv']['queries']
    
    def get_max_results_per_query(self) -> int:
        return self._config['arxiv']['max_results_per_query']
    
    def get_max_results_total(self) -> int:
        return self._config['arxiv']['max_results_total']
    
    def get_arxiv_sort_by(self) -> str:
        return self._config['arxiv']['sort_by']
    
    # Gemini 設定
    def get_gemini_model(self) -> str:
        return self._config['gemini']['model']
    
    def get_gemini_temperature(self) -> float:
        return self._config['gemini']['temperature']
    
    def get_gemini_max_tokens(self) -> int:
        return self._config['gemini']['max_output_tokens']
    
    def get_gemini_max_retries(self) -> int:
        return self._config['gemini']['max_retries']
    
    def get_gemini_retry_delay(self) -> float:
        return self._config['gemini']['retry_delay']
    
    # TTS 設定
    def get_tts_language(self) -> str:
        return self._config['tts']['language']
    
    def get_tts_slow(self) -> bool:
        return self._config['tts']['slow']
    
    def get_tts_max_retries(self) -> int:
        return self._config['tts']['max_retries']
    
    # 提示詞
    def get_translation_prompt(self) -> str:
        return self._config['prompts']['translation']
    
    # 並行處理設定
    def get_max_workers(self) -> int:
        return self._config['concurrency']['max_workers']
    
    def is_async_enabled(self) -> bool:
        return self._config['concurrency']['enable_async']
    
    # 日誌設定
    def get_log_level(self) -> str:
        return self._config['logging']['level']
    
    def get_log_format(self) -> str:
        return self._config['logging']['format']
    
    def is_file_handler_enabled(self) -> bool:
        return self._config['logging']['file_handler']
    
    def is_console_handler_enabled(self) -> bool:
        return self._config['logging']['console_handler']
    
    def get_log_max_bytes(self) -> int:
        return self._config['logging']['max_bytes']
    
    def get_log_backup_count(self) -> int:
        return self._config['logging']['backup_count']

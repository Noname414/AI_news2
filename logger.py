"""
日誌管理器
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from config_manager import ConfigManager

class LoggerManager:
    """日誌管理器"""
    
    def __init__(self, config: ConfigManager, name: str = "ai_news_updater"):
        self.config = config
        self.logger_name = name
        self._logger = None
        self.setup_logger()
    
    def setup_logger(self) -> logging.Logger:
        """設定日誌系統"""
        self._logger = logging.getLogger(self.logger_name)
        self._logger.setLevel(getattr(logging, self.config.get_log_level()))
        
        # 清除現有的 handlers
        self._logger.handlers.clear()
        
        formatter = logging.Formatter(self.config.get_log_format())
        
        # 控制台處理器
        if self.config.is_console_handler_enabled():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
        
        # 檔案處理器
        if self.config.is_file_handler_enabled():
            log_file = Path(self.config.get_log_dir()) / "ai_news_updater.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config.get_log_max_bytes(),
                backupCount=self.config.get_log_backup_count(),
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        
        return self._logger
    
    def get_logger(self) -> logging.Logger:
        """取得日誌器"""
        return self._logger
    
    def info(self, message: str, **kwargs):
        """記錄 INFO 等級日誌"""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """記錄 WARNING 等級日誌"""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """記錄 ERROR 等級日誌"""
        self._logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """記錄 DEBUG 等級日誌"""
        self._logger.debug(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """記錄例外日誌"""
        self._logger.exception(message, **kwargs)

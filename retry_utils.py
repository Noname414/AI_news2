"""
重試機制工具
"""
import asyncio
import time
from functools import wraps
from typing import Callable, Any, Optional, Type, Tuple
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    帶指數退避的重試裝飾器
    
    Args:
        max_attempts: 最大重試次數
        backoff_factor: 退避因子
        max_delay: 最大延遲時間（秒）
        exceptions: 需要重試的例外類型
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff_factor, max=max_delay),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )

def async_retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    異步函數的重試裝飾器
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(backoff_factor * (2 ** attempt), max_delay)
                        logger.warning(
                            f"函數 {func.__name__} 第 {attempt + 1} 次嘗試失敗: {e}，"
                            f"將在 {delay:.2f} 秒後重試"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"函數 {func.__name__} 重試 {max_attempts} 次後仍失敗")
                        
            raise last_exception
        
        return wrapper
    return decorator

class CircuitBreaker:
    """熔斷器模式實現"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """執行函數調用"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("熔斷器狀態變更為 HALF_OPEN")
            else:
                raise Exception("熔斷器開啟中，拒絕請求")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """成功時的處理"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("熔斷器狀態變更為 CLOSED")
    
    def _on_failure(self):
        """失敗時的處理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"熔斷器開啟，失敗次數: {self.failure_count}")

class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """取得執行許可"""
        now = time.time()
        
        # 清理過期的調用記錄
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.time_window]
        
        if len(self.calls) >= self.max_calls:
            # 計算需要等待的時間
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call)
            if wait_time > 0:
                logger.info(f"速率限制啟動，等待 {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)
        
        self.calls.append(now)

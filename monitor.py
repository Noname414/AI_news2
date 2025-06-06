"""
監控和健康檢查模組
"""
import os
import time
import psutil
import sqlite3
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta

from config_manager import ConfigManager
from models import DatabaseManager

class SystemMonitor:
    """系統監控器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.db = DatabaseManager(config.get_database_url())
    
    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_usage": self._get_memory_usage(),
            "disk_usage": self._get_disk_usage(),
            "process_info": self._get_process_info()
        }
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """取得記憶體使用情況"""
        memory = psutil.virtual_memory()
        return {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "percent": memory.percent
        }
    
    def _get_disk_usage(self) -> Dict[str, float]:
        """取得磁碟使用情況"""
        disk = psutil.disk_usage('.')
        return {
            "total_gb": disk.total / (1024**3),
            "used_gb": disk.used / (1024**3),
            "free_gb": disk.free / (1024**3),
            "percent": (disk.used / disk.total) * 100
        }
    
    def _get_process_info(self) -> Dict[str, Any]:
        """取得程序資訊"""
        process = psutil.Process()
        return {
            "pid": process.pid,
            "memory_mb": process.memory_info().rss / (1024**2),
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads()
        }
    
    def check_database_health(self) -> Dict[str, Any]:
        """檢查資料庫健康狀態"""
        try:
            with self.db.get_session() as session:
                # 檢查資料庫連線
                session.execute("SELECT 1")
                
                # 取得統計資訊
                from models import Paper, ProcessingLog
                
                total_papers = session.query(Paper).count()
                processed_papers = session.query(Paper).filter(Paper.processed == True).count()
                failed_papers = session.query(Paper).filter(Paper.processed == False).count()
                
                # 最近的錯誤
                recent_errors = session.query(ProcessingLog).filter(
                    ProcessingLog.status == "error",
                    ProcessingLog.created_at >= datetime.now() - timedelta(hours=24)
                ).count()
                
                return {
                    "status": "healthy",
                    "total_papers": total_papers,
                    "processed_papers": processed_papers,
                    "failed_papers": failed_papers,
                    "recent_errors_24h": recent_errors,
                    "processing_rate": (processed_papers / total_papers * 100) if total_papers > 0 else 0
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_file_system_health(self) -> Dict[str, Any]:
        """檢查檔案系統健康狀態"""
        try:
            audio_dir = Path(self.config.get_audio_dir())
            log_dir = Path(self.config.get_log_dir())
            
            # 檢查目錄是否存在和可寫入
            directories_status = {}
            for name, path in [("audio", audio_dir), ("logs", log_dir)]:
                directories_status[name] = {
                    "exists": path.exists(),
                    "writable": path.exists() and os.access(path, os.W_OK),
                    "size_mb": self._get_directory_size(path) / (1024**2) if path.exists() else 0
                }
            
            # 檢查音訊檔案數量
            audio_files = len(list(audio_dir.glob("*.mp3"))) if audio_dir.exists() else 0
            
            return {
                "status": "healthy",
                "directories": directories_status,
                "audio_files_count": audio_files
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _get_directory_size(self, path: Path) -> int:
        """取得目錄大小"""
        total_size = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """取得處理統計資訊"""
        try:
            with self.db.get_session() as session:
                from models import ProcessingLog
                
                # 最近 24 小時的處理統計
                since = datetime.now() - timedelta(hours=24)
                
                operations = session.query(ProcessingLog).filter(
                    ProcessingLog.created_at >= since
                ).all()
                
                stats = {
                    "total_operations": len(operations),
                    "by_operation": {},
                    "by_status": {},
                    "error_rate": 0
                }
                
                for op in operations:
                    # 按操作類型統計
                    if op.operation not in stats["by_operation"]:
                        stats["by_operation"][op.operation] = {"total": 0, "success": 0, "error": 0}
                    
                    stats["by_operation"][op.operation]["total"] += 1
                    if op.status == "success":
                        stats["by_operation"][op.operation]["success"] += 1
                    elif op.status == "error":
                        stats["by_operation"][op.operation]["error"] += 1
                    
                    # 按狀態統計
                    if op.status not in stats["by_status"]:
                        stats["by_status"][op.status] = 0
                    stats["by_status"][op.status] += 1
                
                # 計算錯誤率
                if stats["total_operations"] > 0:
                    error_count = stats["by_status"].get("error", 0)
                    stats["error_rate"] = (error_count / stats["total_operations"]) * 100
                
                return stats
                
        except Exception as e:
            return {"error": str(e)}
    
    def generate_health_report(self) -> Dict[str, Any]:
        """生成完整的健康報告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": self.get_system_status(),
            "database": self.check_database_health(),
            "filesystem": self.check_file_system_health(),
            "processing_stats": self.get_processing_statistics()
        }

class AlertManager:
    """警報管理器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.monitor = SystemMonitor(config)
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """檢查是否需要發出警報"""
        alerts = []
        
        # 檢查系統資源
        system_status = self.monitor.get_system_status()
        
        if system_status["cpu_percent"] > 90:
            alerts.append({
                "level": "warning",
                "type": "high_cpu",
                "message": f"CPU 使用率過高: {system_status['cpu_percent']:.1f}%"
            })
        
        if system_status["memory_usage"]["percent"] > 90:
            alerts.append({
                "level": "warning",
                "type": "high_memory",
                "message": f"記憶體使用率過高: {system_status['memory_usage']['percent']:.1f}%"
            })
        
        # 檢查資料庫健康狀態
        db_health = self.monitor.check_database_health()
        if db_health.get("status") == "unhealthy":
            alerts.append({
                "level": "critical",
                "type": "database_error",
                "message": f"資料庫連線失敗: {db_health.get('error')}"
            })
        
        # 檢查處理錯誤率
        processing_stats = self.monitor.get_processing_statistics()
        if processing_stats.get("error_rate", 0) > 50:
            alerts.append({
                "level": "warning",
                "type": "high_error_rate",
                "message": f"處理錯誤率過高: {processing_stats['error_rate']:.1f}%"
            })
        
        return alerts

def main():
    """監控主函數"""
    import json
    
    config = ConfigManager()
    monitor = SystemMonitor(config)
    alert_manager = AlertManager(config)
    
    # 生成健康報告
    health_report = monitor.generate_health_report()
    print("=== 系統健康報告 ===")
    print(json.dumps(health_report, indent=2, ensure_ascii=False))
    
    # 檢查警報
    alerts = alert_manager.check_alerts()
    if alerts:
        print("\n=== 警報 ===")
        for alert in alerts:
            print(f"[{alert['level'].upper()}] {alert['type']}: {alert['message']}")
    else:
        print("\n✅ 沒有警報")

if __name__ == "__main__":
    main()

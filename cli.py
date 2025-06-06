"""
命令列介面
"""
import asyncio
import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box

from config_manager import ConfigManager
from news_updater_v2 import AINewsUpdater
from monitor import SystemMonitor, AlertManager

console = Console()

def create_parser():
    """建立命令列參數解析器"""
    parser = argparse.ArgumentParser(
        description="AI 新聞更新器 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python cli.py run                    # 執行完整更新流程
  python cli.py status                 # 查看系統狀態
  python cli.py monitor               # 執行監控檢查
  python cli.py config --show         # 顯示設定
  python cli.py database --stats      # 顯示資料庫統計
"""
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="設定檔路徑 (預設: config.yaml)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="顯示詳細資訊"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用的命令")
    
    # run 命令
    run_parser = subparsers.add_parser("run", help="執行新聞更新")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模擬執行，不實際處理"
    )
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="查看系統狀態")
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式輸出"
    )
    
    # monitor 命令
    monitor_parser = subparsers.add_parser("monitor", help="執行監控檢查")
    monitor_parser.add_argument(
        "--alerts-only",
        action="store_true",
        help="只顯示警報"
    )
    
    # config 命令
    config_parser = subparsers.add_parser("config", help="設定管理")
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="顯示目前設定"
    )
    config_parser.add_argument(
        "--validate",
        action="store_true",
        help="驗證設定檔"
    )
    
    # database 命令
    db_parser = subparsers.add_parser("database", help="資料庫管理")
    db_parser.add_argument(
        "--stats",
        action="store_true",
        help="顯示資料庫統計"
    )
    db_parser.add_argument(
        "--export",
        help="匯出資料到指定檔案"
    )
      # benchmark 命令
    benchmark_parser = subparsers.add_parser("benchmark", help="性能基準測試")
    benchmark_parser.add_argument(
        "--save-results",
        action="store_true",
        help="將基準測試結果儲存到檔案"
    )
    
    # test 命令
    test_parser = subparsers.add_parser("test", help="系統測試")
    test_parser.add_argument(
        "--integration",
        action="store_true",
        help="執行系統集成測試"
    )
    test_parser.add_argument(
        "--coverage",
        action="store_true",
        help="生成測試覆蓋率報告"
    )
    
    return parser

async def cmd_run(args):
    """執行新聞更新命令"""
    try:
        if args.dry_run:
            console.print("[yellow]🔍 模擬執行模式[/yellow]")
            # TODO: 實作模擬執行邏輯
            return
        
        updater = AINewsUpdater(args.config)
        await updater.run()
        
    except Exception as e:
        console.print(f"[bold red]❌ 執行失敗: {e}[/bold red]")
        sys.exit(1)

def cmd_status(args):
    """查看系統狀態命令"""
    try:
        config = ConfigManager(args.config)
        monitor = SystemMonitor(config)
        
        if args.json:
            import json
            status = monitor.generate_health_report()
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            _display_status_table(monitor)
            
    except Exception as e:
        console.print(f"[bold red]❌ 取得狀態失敗: {e}[/bold red]")
        sys.exit(1)

def _display_status_table(monitor):
    """顯示狀態表格"""
    health_report = monitor.generate_health_report()
    
    # 系統狀態表格
    table = Table(title="🖥️  系統狀態", box=box.ROUNDED)
    table.add_column("項目", style="cyan")
    table.add_column("數值", style="magenta")
    table.add_column("狀態", style="green")
    
    system = health_report["system"]
    table.add_row("CPU 使用率", f"{system['cpu_percent']:.1f}%", 
                 "🟢 正常" if system['cpu_percent'] < 80 else "🟡 高負載")
    table.add_row("記憶體使用率", f"{system['memory_usage']['percent']:.1f}%",
                 "🟢 正常" if system['memory_usage']['percent'] < 80 else "🟡 高負載")
    
    console.print(table)
    
    # 資料庫狀態表格
    db_table = Table(title="💾 資料庫狀態", box=box.ROUNDED)
    db_table.add_column("項目", style="cyan")
    db_table.add_column("數值", style="magenta")
    
    db = health_report["database"]
    if db.get("status") == "healthy":
        db_table.add_row("總論文數", str(db.get("total_papers", 0)))
        db_table.add_row("已處理數", str(db.get("processed_papers", 0)))
        db_table.add_row("處理率", f"{db.get('processing_rate', 0):.1f}%")
        db_table.add_row("24小時錯誤數", str(db.get("recent_errors_24h", 0)))
    else:
        db_table.add_row("狀態", "❌ 連線失敗")
    
    console.print(db_table)

def cmd_monitor(args):
    """執行監控檢查命令"""
    try:
        config = ConfigManager(args.config)
        alert_manager = AlertManager(config)
        
        alerts = alert_manager.check_alerts()
        
        if args.alerts_only:
            if alerts:
                for alert in alerts:
                    level_icon = "🔴" if alert["level"] == "critical" else "🟡"
                    console.print(f"{level_icon} [{alert['level'].upper()}] {alert['message']}")
            else:
                console.print("✅ 沒有警報")
        else:
            # 顯示完整監控報告
            monitor = SystemMonitor(config)
            _display_status_table(monitor)
            
            if alerts:
                console.print("\n⚠️  警報:")
                for alert in alerts:
                    level_icon = "🔴" if alert["level"] == "critical" else "🟡"
                    console.print(f"  {level_icon} [{alert['level'].upper()}] {alert['message']}")
            else:
                console.print("\n✅ 沒有警報")
                
    except Exception as e:
        console.print(f"[bold red]❌ 監控檢查失敗: {e}[/bold red]")
        sys.exit(1)

def cmd_config(args):
    """設定管理命令"""
    try:
        if args.show:
            config = ConfigManager(args.config)
            
            table = Table(title="⚙️  設定資訊", box=box.ROUNDED)
            table.add_column("設定項目", style="cyan")
            table.add_column("數值", style="magenta")
            
            table.add_row("應用程式名稱", config.get_app_name())
            table.add_row("版本", config.get_app_version())
            table.add_row("資料庫 URL", config.get_database_url())
            table.add_row("查詢詞", ", ".join(config.get_arxiv_queries()))
            table.add_row("每次查詢最大結果", str(config.get_max_results_per_query()))
            table.add_row("Gemini 模型", config.get_gemini_model())
            table.add_row("最大工作執行緒", str(config.get_max_workers()))
            
            console.print(table)
            
        elif args.validate:
            config = ConfigManager(args.config)
            console.print("✅ 設定檔驗證通過")
            
    except Exception as e:
        console.print(f"[bold red]❌ 設定處理失敗: {e}[/bold red]")
        sys.exit(1)

def cmd_database(args):
    """資料庫管理命令"""
    try:
        config = ConfigManager(args.config)
        
        if args.stats:
            monitor = SystemMonitor(config)
            db_health = monitor.check_database_health()
            processing_stats = monitor.get_processing_statistics()
            
            # 資料庫統計表格
            table = Table(title="📊 資料庫統計", box=box.ROUNDED)
            table.add_column("項目", style="cyan")
            table.add_column("數值", style="magenta")
            
            if db_health.get("status") == "healthy":
                table.add_row("總論文數", str(db_health.get("total_papers", 0)))
                table.add_row("已處理論文數", str(db_health.get("processed_papers", 0)))
                table.add_row("失敗論文數", str(db_health.get("failed_papers", 0)))
                table.add_row("處理成功率", f"{db_health.get('processing_rate', 0):.1f}%")
                table.add_row("24小時錯誤數", str(db_health.get("recent_errors_24h", 0)))
                
                if processing_stats and "error_rate" in processing_stats:
                    table.add_row("24小時錯誤率", f"{processing_stats['error_rate']:.1f}%")
            else:
                table.add_row("狀態", "❌ 資料庫連線失敗")
            
            console.print(table)
            
        elif args.export:
            from models import DatabaseManager
            db = DatabaseManager(config.get_database_url())
            
            if db.export_to_jsonl(args.export):
                console.print(f"✅ 資料已匯出到 {args.export}")
            else:
                console.print("❌ 匯出失敗")
                
    except Exception as e:
        console.print(f"[bold red]❌ 資料庫操作失敗: {e}[/bold red]")
        sys.exit(1)

async def cmd_benchmark(args):
    """性能基準測試命令"""
    try:
        from benchmark import PerformanceBenchmark
        
        console.print("📊 開始性能基準測試...")
        
        benchmark = PerformanceBenchmark(args.config)
        results = await benchmark.run_all_benchmarks()
        
        console.print("✅ 基準測試完成")
        
        if args.save_results:
            import json
            import time
            results_file = f"benchmark_results_{int(time.time())}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            console.print(f"📄 結果已保存到: {results_file}")
        
    except Exception as e:
        console.print(f"[bold red]❌ 基準測試失敗: {e}[/bold red]")
        sys.exit(1)

async def cmd_test(args):
    """系統測試命令"""
    try:
        if args.integration:
            from integration_test import SystemIntegrationTest
            console.print("🧪 開始集成測試...")
            
            tester = SystemIntegrationTest()
            success = await tester.run_all_tests()
            
            if success:
                console.print("✅ 所有測試通過")
            else:
                console.print("❌ 部分測試失敗")
                sys.exit(1)
        else:
            # 運行單元測試
            import subprocess
            console.print("🧪 開始單元測試...")
            
            cmd = ["python", "-m", "pytest", "test_updater.py", "-v"]
            if args.coverage:
                cmd.extend(["--cov=.", "--cov-report=html"])
            
            result = subprocess.run(cmd)
            
            if result.returncode == 0:
                console.print("✅ 單元測試通過")
            else:
                console.print("❌ 單元測試失敗")
                sys.exit(1)
        
    except Exception as e:
        console.print(f"[bold red]❌ 測試執行失敗: {e}[/bold red]")
        sys.exit(1)

async def main():
    """主函數"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 檢查設定檔是否存在
    if not Path(args.config).exists():
        console.print(f"[bold red]❌ 設定檔不存在: {args.config}[/bold red]")
        sys.exit(1)
      # 執行對應的命令    if args.command == "run":
        await cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "database":
        cmd_database(args)
    elif args.command == "benchmark":
        await cmd_benchmark(args)
    elif args.command == "test":
        await cmd_test(args)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 使用者中斷執行[/yellow]")
    except Exception as e:
        console.print(f"[bold red]💥 程式執行失敗: {e}[/bold red]")
        sys.exit(1)

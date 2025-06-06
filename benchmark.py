#!/usr/bin/env python3
"""
性能基準測試腳本
測試系統在不同負載下的性能表現
"""

import asyncio
import time
import statistics
import psutil
from typing import List, Dict, Any
from pathlib import Path
import json

from config_manager import ConfigManager
from models import DatabaseManager
from news_updater_v2 import AINewsUpdater
from logger import get_logger

logger = get_logger(__name__)

class PerformanceBenchmark:
    """性能基準測試"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager(config_path)
        self.results = []
    
    async def benchmark_database_operations(self, num_operations: int = 1000) -> Dict[str, Any]:
        """基準測試數據庫操作"""
        logger.info(f"開始數據庫操作基準測試（{num_operations} 次操作）...")
        
        db_manager = DatabaseManager(self.config.get_database_url())
        await db_manager.init_database()
        
        # 測試插入性能
        start_time = time.time()
        insert_times = []
        
        for i in range(num_operations):
            paper_id = f"benchmark_paper_{i:06d}"
            op_start = time.time()
            await db_manager.mark_paper_processed(paper_id)
            op_end = time.time()
            insert_times.append(op_end - op_start)
        
        insert_duration = time.time() - start_time
        
        # 測試查詢性能
        start_time = time.time()
        query_times = []
        
        for i in range(0, min(num_operations, 100)):  # 只測試前100個
            paper_id = f"benchmark_paper_{i:06d}"
            op_start = time.time()
            await db_manager.is_paper_processed(paper_id)
            op_end = time.time()
            query_times.append(op_end - op_start)
        
        query_duration = time.time() - start_time
        
        return {
            'num_operations': num_operations,
            'insert_duration': insert_duration,
            'insert_avg_time': statistics.mean(insert_times),
            'insert_ops_per_sec': num_operations / insert_duration,
            'query_duration': query_duration,
            'query_avg_time': statistics.mean(query_times),
            'query_ops_per_sec': len(query_times) / query_duration
        }
    
    async def benchmark_concurrent_processing(self, num_papers: int = 10) -> Dict[str, Any]:
        """基準測試並發處理"""
        logger.info(f"開始並發處理基準測試（{num_papers} 篇論文）...")
        
        # 模擬論文數據
        mock_papers = []
        for i in range(num_papers):
            mock_papers.append({
                'id': f'benchmark_{i:04d}.{int(time.time())}',
                'title': f'Benchmark Paper {i}',
                'summary': f'This is a benchmark paper number {i} for testing purposes.',
                'authors': [f'Author {i}A', f'Author {i}B'],
                'published': '2024-01-01',
                'pdf_url': f'https://arxiv.org/pdf/benchmark_{i:04d}.pdf',
                'categories': ['cs.AI']
            })
        
        updater = AINewsUpdater(self.config)
        
        # 測試不同並發級別
        concurrency_levels = [1, 2, 4, 8]
        results = {}
        
        for max_workers in concurrency_levels:
            if max_workers > num_papers:
                continue
                
            logger.info(f"測試並發級別: {max_workers}")
            
            # 更新配置
            original_workers = self.config.get('concurrency.max_workers')
            self.config.data['concurrency']['max_workers'] = max_workers
            
            start_time = time.time()
            start_cpu = psutil.cpu_percent()
            start_memory = psutil.virtual_memory().percent
            
            # 模擬處理（不實際調用 API）
            async def mock_process_paper(paper):
                # 模擬處理時間
                await asyncio.sleep(0.1)
                return {
                    **paper,
                    'translated_title': f"翻譯標題 {paper['id']}",
                    'translated_abstract': f"翻譯摘要 {paper['id']}",
                    'audio_path': f"audio_{paper['id']}.mp3"
                }
            
            # 執行並發處理
            semaphore = asyncio.Semaphore(max_workers)
            
            async def process_with_semaphore(paper):
                async with semaphore:
                    return await mock_process_paper(paper)
            
            tasks = [process_with_semaphore(paper) for paper in mock_papers]
            processed_papers = await asyncio.gather(*tasks)
            
            end_time = time.time()
            end_cpu = psutil.cpu_percent()
            end_memory = psutil.virtual_memory().percent
            
            duration = end_time - start_time
            throughput = len(processed_papers) / duration
            
            results[max_workers] = {
                'duration': duration,
                'throughput': throughput,
                'cpu_usage_delta': end_cpu - start_cpu,
                'memory_usage_delta': end_memory - start_memory,
                'processed_count': len(processed_papers)
            }
            
            # 恢復原始配置
            self.config.data['concurrency']['max_workers'] = original_workers
        
        return {
            'num_papers': num_papers,
            'concurrency_results': results
        }
    
    async def benchmark_memory_usage(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """基準測試內存使用情況"""
        logger.info(f"開始內存使用基準測試（{duration_seconds} 秒）...")
        
        process = psutil.Process()
        memory_samples = []
        cpu_samples = []
        
        start_time = time.time()
        
        # 創建一些負載
        updater = AINewsUpdater(self.config)
        await updater.db_manager.init_database()
        
        while time.time() - start_time < duration_seconds:
            # 記錄系統指標
            memory_info = process.memory_info()
            memory_samples.append(memory_info.rss / 1024 / 1024)  # MB
            cpu_samples.append(process.cpu_percent())
            
            # 模擬一些工作負載
            for i in range(10):
                paper_id = f"memory_test_{int(time.time())}_{i}"
                await updater.db_manager.mark_paper_processed(paper_id)
            
            await asyncio.sleep(1)
        
        return {
            'duration': duration_seconds,
            'memory_usage_mb': {
                'min': min(memory_samples),
                'max': max(memory_samples),
                'avg': statistics.mean(memory_samples),
                'median': statistics.median(memory_samples)
            },
            'cpu_usage_percent': {
                'min': min(cpu_samples),
                'max': max(cpu_samples),
                'avg': statistics.mean(cpu_samples),
                'median': statistics.median(cpu_samples)
            }
        }
    
    async def benchmark_file_operations(self, num_files: int = 100) -> Dict[str, Any]:
        """基準測試文件操作"""
        logger.info(f"開始文件操作基準測試（{num_files} 個文件）...")
        
        test_dir = Path("benchmark_files")
        test_dir.mkdir(exist_ok=True)
        
        try:
            # 測試文件寫入
            start_time = time.time()
            write_times = []
            
            for i in range(num_files):
                file_path = test_dir / f"test_file_{i:04d}.json"
                test_data = {
                    'id': f'test_{i}',
                    'title': f'Test File {i}',
                    'content': 'This is test content for file operations benchmark' * 10
                }
                
                op_start = time.time()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(test_data, f, ensure_ascii=False, indent=2)
                op_end = time.time()
                write_times.append(op_end - op_start)
            
            write_duration = time.time() - start_time
            
            # 測試文件讀取
            start_time = time.time()
            read_times = []
            
            for i in range(num_files):
                file_path = test_dir / f"test_file_{i:04d}.json"
                
                op_start = time.time()
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                op_end = time.time()
                read_times.append(op_end - op_start)
            
            read_duration = time.time() - start_time
            
            return {
                'num_files': num_files,
                'write_duration': write_duration,
                'write_avg_time': statistics.mean(write_times),
                'write_ops_per_sec': num_files / write_duration,
                'read_duration': read_duration,
                'read_avg_time': statistics.mean(read_times),
                'read_ops_per_sec': num_files / read_duration
            }
            
        finally:
            # 清理測試文件
            import shutil
            if test_dir.exists():
                shutil.rmtree(test_dir)
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """運行所有基準測試"""
        logger.info("開始運行性能基準測試...")
        
        start_time = time.time()
        
        benchmarks = {
            'database_operations': await self.benchmark_database_operations(500),
            'concurrent_processing': await self.benchmark_concurrent_processing(20),
            'memory_usage': await self.benchmark_memory_usage(30),
            'file_operations': await self.benchmark_file_operations(50)
        }
        
        total_duration = time.time() - start_time
        
        # 系統信息
        system_info = {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'python_version': __import__('sys').version
        }
        
        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_duration': total_duration,
            'system_info': system_info,
            'benchmarks': benchmarks
        }
        
        # 保存結果
        results_file = Path(f"benchmark_results_{int(time.time())}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"基準測試完成，結果保存至: {results_file}")
        
        # 輸出摘要
        self._print_benchmark_summary(results)
        
        return results
    
    def _print_benchmark_summary(self, results: Dict[str, Any]):
        """打印基準測試摘要"""
        print("\n" + "="*60)
        print("         性能基準測試摘要")
        print("="*60)
        
        db_results = results['benchmarks']['database_operations']
        print(f"\n📊 數據庫操作:")
        print(f"   插入操作: {db_results['insert_ops_per_sec']:.1f} ops/sec")
        print(f"   查詢操作: {db_results['query_ops_per_sec']:.1f} ops/sec")
        
        concurrent_results = results['benchmarks']['concurrent_processing']
        print(f"\n🚀 並發處理:")
        for workers, result in concurrent_results['concurrency_results'].items():
            print(f"   {workers} 並發: {result['throughput']:.2f} papers/sec")
        
        memory_results = results['benchmarks']['memory_usage']
        print(f"\n💾 內存使用:")
        print(f"   平均: {memory_results['memory_usage_mb']['avg']:.1f} MB")
        print(f"   峰值: {memory_results['memory_usage_mb']['max']:.1f} MB")
        
        file_results = results['benchmarks']['file_operations']
        print(f"\n📁 文件操作:")
        print(f"   寫入: {file_results['write_ops_per_sec']:.1f} files/sec")
        print(f"   讀取: {file_results['read_ops_per_sec']:.1f} files/sec")
        
        print(f"\n⏱️  總測試時間: {results['total_duration']:.1f} 秒")
        print("="*60)

async def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='性能基準測試工具')
    parser.add_argument('--config', default='config.yaml', help='配置文件路徑')
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(args.config)
    await benchmark.run_all_benchmarks()

if __name__ == "__main__":
    asyncio.run(main())

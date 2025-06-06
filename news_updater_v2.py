"""
AI 新聞更新器 v2.0
重構版本，具備更好的錯誤處理、並行處理和可維護性
"""
import asyncio
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import arxiv
from gtts import gTTS
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from config_manager import ConfigManager
from logger import LoggerManager
from models import DatabaseManager, Paper
from retry_utils import retry_with_backoff, async_retry_with_backoff, RateLimiter

console = Console()

class PaperTranslation(BaseModel):
    """論文翻譯結果的結構化模型"""
    title_zh: str = Field(description="論文的繁體中文標題")
    summary_zh: str = Field(description="適合收聽的簡明中文摘要")
    applications: List[str] = Field(
        description="三個生活化應用場景的描述",
        min_items=3,
        max_items=3
    )
    pitch: str = Field(description="向創投或天使基金推銷的內容")

class AINewsUpdater:
    """AI 新聞更新器主類別"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager(config_path)
        self.logger = LoggerManager(self.config).get_logger()
        self.db = DatabaseManager(self.config.get_database_url())
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # 初始化速率限制器（每分鐘最多 60 次請求）
        self.rate_limiter = RateLimiter(max_calls=60, time_window=60.0)
        
        # 建立必要的資料表
        self.db.create_tables()
        
        self.logger.info(f"AI 新聞更新器 v{self.config.get_app_version()} 啟動")
    
    @retry_with_backoff(max_attempts=3, exceptions=(Exception,))
    def fetch_papers_for_query(self, query: str) -> List[Dict[str, Any]]:
        """為特定查詢詞抓取論文"""
        self.logger.info(f"開始抓取查詢: {query}")
        
        processed_ids = self.db.get_processed_ids()
        client_arxiv = arxiv.Client()
        
        # 根據設定的排序方式決定 sort_by
        sort_by = getattr(arxiv.SortCriterion, self.config.get_arxiv_sort_by())
        
        search = arxiv.Search(
            query=f'"{query}"',
            max_results=self.config.get_max_results_total(),
            sort_by=sort_by
        )
        
        papers = []
        count = 0
        max_per_query = self.config.get_max_results_per_query()
        
        try:
            for result in client_arxiv.results(search):
                if count >= max_per_query:
                    break
                    
                paper_id = result.get_short_id()
                
                # 跳過已處理的論文
                if paper_id in processed_ids:
                    continue
                
                paper_data = {
                    "id": paper_id,
                    "query": query,
                    "url": result.entry_id,
                    "title": result.title,
                    "summary": result.summary,
                    "authors": [author.name for author in result.authors],
                    "published_date": result.published.strftime("%Y-%m-%d"),
                }
                
                # 儲存到資料庫
                if self.db.save_paper(paper_data):
                    papers.append(paper_data)
                    count += 1
                    self.db.log_operation(paper_id, "fetch", "success", f"成功抓取論文: {result.title}")
                else:
                    self.db.log_operation(paper_id, "fetch", "error", "儲存論文失敗")
                
        except Exception as e:
            self.logger.error(f"抓取查詢 {query} 時發生錯誤: {e}")
            raise
        
        self.logger.info(f"查詢 {query} 完成，抓取到 {len(papers)} 篇新論文")
        return papers
    
    async def fetch_all_papers(self) -> List[Dict[str, Any]]:
        """抓取所有查詢的論文"""
        all_papers = []
        queries = self.config.get_arxiv_queries()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("抓取論文中...", total=len(queries))
            
            for query in queries:
                try:
                    papers = self.fetch_papers_for_query(query)
                    all_papers.extend(papers)
                    progress.update(task, advance=1, description=f"已完成查詢: {query}")
                except Exception as e:
                    self.logger.error(f"查詢 {query} 失敗: {e}")
                    progress.update(task, advance=1, description=f"查詢失敗: {query}")
        
        self.logger.info(f"總共抓取到 {len(all_papers)} 篇新論文")
        return all_papers
    
    @async_retry_with_backoff(max_attempts=3, exceptions=(Exception,))
    async def translate_paper(self, paper_id: str, title: str, summary: str) -> Dict[str, Any]:
        """翻譯論文標題和摘要"""
        await self.rate_limiter.acquire()
        
        prompt = self.config.get_translation_prompt().format(
            title=title,
            summary=summary
        )
        
        try:
            response = await asyncio.to_thread(
                self.gemini_client.models.generate_content,
                model=self.config.get_gemini_model(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=PaperTranslation,
                    temperature=self.config.get_gemini_temperature(),
                    max_output_tokens=self.config.get_gemini_max_tokens(),
                )
            )
            
            result = response.parsed
            translation_data = {
                "title_zh": result.title_zh,
                "summary_zh": result.summary_zh,
                "applications": result.applications,
                "pitch": result.pitch
            }
            
            # 更新資料庫
            if self.db.update_paper_translation(paper_id, translation_data):
                self.db.log_operation(paper_id, "translate", "success", "翻譯完成")
                self.logger.info(f"論文 {paper_id} 翻譯完成")
            else:
                self.db.log_operation(paper_id, "translate", "error", "更新翻譯資料失敗")
            
            return translation_data
            
        except Exception as e:
            self.logger.error(f"翻譯論文 {paper_id} 失敗: {e}")
            self.db.log_operation(paper_id, "translate", "error", str(e))
            
            # 回退方案
            fallback_data = {
                "title_zh": f"[翻譯失敗] {title}",
                "summary_zh": f"摘要翻譯失敗：{str(e)}",
                "applications": ["應用場景1：翻譯失敗", "應用場景2：翻譯失敗", "應用場景3：翻譯失敗"],
                "pitch": "推銷內容翻譯失敗"
            }
            return fallback_data
    
    @async_retry_with_backoff(max_attempts=3, exceptions=(Exception,))
    async def generate_audio(self, paper_id: str, content: str) -> Optional[str]:
        """生成音訊檔案"""
        audio_path = Path(self.config.get_audio_dir()) / f"{paper_id}.mp3"
        
        try:
            # 使用 asyncio.to_thread 避免阻塞
            await asyncio.to_thread(self._create_audio_file, content, str(audio_path))
            
            # 更新資料庫
            if self.db.update_paper_audio(paper_id, str(audio_path)):
                self.db.log_operation(paper_id, "audio", "success", "音訊生成完成")
                self.logger.info(f"論文 {paper_id} 音訊生成完成")
                return str(audio_path)
            else:
                self.db.log_operation(paper_id, "audio", "error", "更新音訊路徑失敗")
                return None
                
        except Exception as e:
            self.logger.error(f"生成論文 {paper_id} 音訊失敗: {e}")
            self.db.log_operation(paper_id, "audio", "error", str(e))
            return None
    
    def _create_audio_file(self, text: str, filename: str):
        """建立音訊檔案（同步函數）"""
        tts = gTTS(
            text=text,
            lang=self.config.get_tts_language(),
            slow=self.config.get_tts_slow()
        )
        tts.save(filename)
    
    async def process_papers(self, papers: List[Dict[str, Any]]):
        """處理論文列表"""
        if not papers:
            self.logger.info("沒有需要處理的論文")
            return
        
        semaphore = asyncio.Semaphore(self.config.get_max_workers())
        
        async def process_single_paper(paper: Dict[str, Any]):
            async with semaphore:
                paper_id = paper["id"]
                
                # 翻譯
                translation = await self.translate_paper(
                    paper_id, paper["title"], paper["summary"]
                )
                
                # 組合音訊內容
                audio_content = self._create_audio_content(translation)
                
                # 生成音訊
                await self.generate_audio(paper_id, audio_content)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("處理論文中...", total=len(papers))
            
            # 並行處理所有論文
            tasks = []
            for paper in papers:
                task_coro = process_single_paper(paper)
                tasks.append(task_coro)
            
            # 批次執行
            for completed_task in asyncio.as_completed(tasks):
                try:
                    await completed_task
                    progress.update(task, advance=1)
                except Exception as e:
                    self.logger.error(f"處理論文時發生錯誤: {e}")
                    progress.update(task, advance=1)
    
    def _create_audio_content(self, translation: Dict[str, Any]) -> str:
        """建立音訊內容"""
        return (
            f"{translation['title_zh']}\n\n"
            f"{translation['summary_zh']}\n\n"
            f"這項技術有三個生活化的應用場景：\n"
            f"第一，{translation['applications'][0]}\n"
            f"第二，{translation['applications'][1]}\n"
            f"第三，{translation['applications'][2]}\n\n"
            f"如果向創投或天使基金推銷，可以這樣說：\n{translation['pitch']}"
        )
    
    def export_to_jsonl(self):
        """匯出處理完成的論文到 JSONL 檔案"""
        output_path = self.config.get_news_jsonl_path()
        if self.db.export_to_jsonl(output_path):
            self.logger.info(f"成功匯出到 {output_path}")
        else:
            self.logger.error("匯出 JSONL 失敗")
    
    async def run(self):
        """執行主流程"""
        try:
            console.print(f"[bold green]🚀 {self.config.get_app_name()} v{self.config.get_app_version()} 開始執行[/bold green]")
            
            # 1. 抓取論文
            papers = await self.fetch_all_papers()
            
            if not papers:
                console.print("[yellow]⚠️  沒有發現新的論文，結束執行[/yellow]")
                return
            
            # 2. 處理論文
            await self.process_papers(papers)
            
            # 3. 匯出結果
            self.export_to_jsonl()
            
            console.print(f"[bold green]✅ 處理完成！總共處理了 {len(papers)} 篇論文[/bold green]")
            
        except Exception as e:
            self.logger.exception(f"執行過程中發生錯誤: {e}")
            console.print(f"[bold red]❌ 執行失敗: {e}[/bold red]")
            raise

async def main():
    """主函數"""
    try:
        updater = AINewsUpdater()
        await updater.run()
    except KeyboardInterrupt:
        console.print("[yellow]👋 使用者中斷執行[/yellow]")
    except Exception as e:
        console.print(f"[bold red]💥 程式執行失敗: {e}[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())

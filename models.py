"""
資料庫模型定義
"""
from datetime import datetime
from typing import List
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()

class Paper(Base):
    """論文資料模型"""
    __tablename__ = "papers"
    
    id = Column(String, primary_key=True)  # arXiv ID
    query = Column(String, nullable=False)  # 搜尋查詢詞
    url = Column(String, nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    authors = Column(JSON, nullable=False)  # 作者列表
    published_date = Column(String, nullable=False)
    
    # 翻譯結果
    title_zh = Column(Text)
    summary_zh = Column(Text)
    applications = Column(JSON)  # 應用場景列表
    pitch = Column(Text)
    
    # 音訊檔案路徑
    audio_path = Column(String)
    
    # 處理狀態
    processed = Column(Boolean, default=False)
    translation_attempts = Column(Integer, default=0)
    audio_attempts = Column(Integer, default=0)
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProcessingLog(Base):
    """處理日誌模型"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(String, nullable=False)
    operation = Column(String, nullable=False)  # fetch, translate, audio
    status = Column(String, nullable=False)  # success, error, retry
    message = Column(Text)
    error_details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """資料庫管理器"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        """建立資料表"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """取得資料庫 session"""
        return self.SessionLocal()
        
    def get_processed_ids(self) -> set:
        """取得已處理的論文 ID"""
        with self.get_session() as session:
            processed_papers = session.query(Paper.id).filter(Paper.processed == True).all()
            return {paper.id for paper in processed_papers}
            
    def save_paper(self, paper_data: dict) -> bool:
        """儲存論文資料"""
        try:
            with self.get_session() as session:
                paper = Paper(**paper_data)
                session.merge(paper)  # 使用 merge 處理重複
                session.commit()
                return True
        except Exception as e:
            print(f"儲存論文資料失敗: {e}")
            return False
            
    def update_paper_translation(self, paper_id: str, translation_data: dict) -> bool:
        """更新論文翻譯資料"""
        try:
            with self.get_session() as session:
                paper = session.query(Paper).filter(Paper.id == paper_id).first()
                if paper:
                    for key, value in translation_data.items():
                        setattr(paper, key, value)
                    paper.updated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"更新翻譯資料失敗: {e}")
            return False
            
    def update_paper_audio(self, paper_id: str, audio_path: str) -> bool:
        """更新論文音訊路徑"""
        try:
            with self.get_session() as session:
                paper = session.query(Paper).filter(Paper.id == paper_id).first()
                if paper:
                    paper.audio_path = audio_path
                    paper.processed = True
                    paper.updated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"更新音訊路徑失敗: {e}")
            return False
            
    def log_operation(self, paper_id: str, operation: str, status: str, 
                     message: str = None, error_details: str = None):
        """記錄操作日誌"""
        try:
            with self.get_session() as session:
                log = ProcessingLog(
                    paper_id=paper_id,
                    operation=operation,
                    status=status,
                    message=message,
                    error_details=error_details
                )
                session.add(log)
                session.commit()
        except Exception as e:
            print(f"記錄日誌失敗: {e}")
            
    def get_unprocessed_papers(self) -> List[Paper]:
        """取得未處理的論文"""
        with self.get_session() as session:
            return session.query(Paper).filter(Paper.processed == False).all()
            
    def export_to_jsonl(self, output_path: str) -> bool:
        """匯出資料到 JSONL 檔案"""
        import json
        try:
            with self.get_session() as session:
                papers = session.query(Paper).filter(Paper.processed == True).all()
                with open(output_path, "w", encoding="utf-8") as f:
                    for paper in papers:
                        paper_dict = {
                            "id": paper.id,
                            "query": paper.query,
                            "url": paper.url,
                            "title": paper.title,
                            "summary": paper.summary,
                            "authors": paper.authors,
                            "published_date": paper.published_date,
                            "title_zh": paper.title_zh,
                            "summary_zh": paper.summary_zh,
                            "applications": paper.applications,
                            "pitch": paper.pitch,
                            "audio": paper.audio_path,
                            "timestamp": paper.updated_at.isoformat() if paper.updated_at else None
                        }
                        f.write(json.dumps(paper_dict, ensure_ascii=False) + "\n")
                return True
        except Exception as e:
            print(f"匯出 JSONL 失敗: {e}")
            return False

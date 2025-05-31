#!/usr/bin/env python3
"""
測試新的結構化輸出翻譯功能
"""

import os
from pydantic import BaseModel, Field
from typing import List
from google import genai
from google.genai import types

# 設定 API 金鑰
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 定義結構化輸出的 Pydantic 模型
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

def test_translation():
    """測試翻譯功能"""
    # 測試用的論文標題和摘要
    test_title = "Attention Is All You Need"
    test_summary = """We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show that these models are superior in quality while being more parallelizable and requiring significantly less time to train."""
    
    prompt = (
        f"請將以下arXiv論文標題與摘要翻譯成繁體中文，並完成以下任務：\n"
        f"1. 將摘要濃縮成適合收聽且簡明扼要的中文摘要（約100-150字）。\n"
        f"2. 設想3個「生活化的應用場景」，用簡單易懂的口語描述，讓一般人能理解這項技術的價值。\n"
        f"3. 以「向創投或天使基金推銷」的角度，說明這項技術的重要性與潛在商業價值，盡量發揮創意、大膽預測未來可能性。\n\n"
        f"英文標題：{test_title}\n"
        f"英文摘要：{test_summary}\n"
    )
    
    try:
        print("🔄 正在測試結構化輸出翻譯功能...")
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=PaperTranslation,
                temperature=0.7,
                max_output_tokens=2000,
            ),
        )
        
        # 使用結構化輸出，直接解析為 Pydantic 模型
        result = response.parsed
        
        print("✅ 翻譯成功！")
        print(f"📝 中文標題: {result.title_zh}")
        print(f"📄 中文摘要: {result.summary_zh}")
        print("🎯 應用場景:")
        for i, app in enumerate(result.applications, 1):
            print(f"   {i}. {app}")
        print(f"💰 創投推銷: {result.pitch}")
        
        # 驗證結構
        assert isinstance(result.title_zh, str), "標題應該是字串"
        assert isinstance(result.summary_zh, str), "摘要應該是字串"
        assert isinstance(result.applications, list), "應用場景應該是列表"
        assert len(result.applications) == 3, "應該有3個應用場景"
        assert isinstance(result.pitch, str), "推銷內容應該是字串"
        
        print("\n✅ 所有驗證通過！結構化輸出功能正常運作。")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ 請設定 GEMINI_API_KEY 環境變數")
        exit(1)
    
    success = test_translation()
    exit(0 if success else 1) 
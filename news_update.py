# update_news.py
import re
import arxiv
import json
import os
from gtts import gTTS
from datetime import datetime
import google.generativeai as genai

NEWS_PATH = "news.jsonl"
PROCESSED_IDS_PATH = "processed_ids.txt"
QUERY = ["AI", "Foundation Model", "Diffusion Model"]

# === 設定 Gemini API 金鑰 ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# === 輔助函式：讀取與儲存已處理的 ID ===
def load_processed_ids(path=PROCESSED_IDS_PATH):
    if not os.path.exists(path):
        return set()
    with open(path, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_processed_ids(ids, path=PROCESSED_IDS_PATH):
    with open(path, "w") as f:
        f.write("\n".join(ids))

# === 抓取 AI 論文摘要 ===
def fetch_ai_papers(query, max_results=50):
    processed_ids = load_processed_ids()
    client = arxiv.Client()
    search = arxiv.Search(
        query=f'"{query}"',
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    papers = []
    for result in client.results(search):
        # 跳過已處理的論文
        if result.get_short_id() in processed_ids:
            continue
        papers.append({
            "query": query,
            "id": result.get_short_id(),
            "url": result.entry_id,
            "title": result.title,
            "summary": result.summary,
            "authors": [author.name for author in result.authors],
            "published_date": result.published.strftime("%Y-%m-%d"),
        })
        # 將新處理的 ID 添加到集合中
        processed_ids.add(result.get_short_id())
        # 每個類別只抓取1篇
        break

    # 在處理完所有論文後，一次性儲存更新後的 ID 集合
    save_processed_ids(processed_ids)
    return papers

# === 使用 Gemini 摘要為繁體中文、生成應用場景與創投推銷點 ===
def summarize_to_chinese(title, summary):
    prompt = (
        f"請將以下arXiv論文標題與摘要翻譯成繁體中文，並完成以下三個任務：\n"
        f"1. 將摘要濃縮成適合收聽且簡明扼要的中文摘要。\n"
        f"2. 設想3個「生活化的應用場景」，用簡單易懂的口語描述，讓一般人能理解這項技術的價值。\n"
        f"3. 以「向創投或天使基金推銷」的角度，說明這項技術的重要性與潛在商業價值，盡量發揮創意、大膽預測未來可能性。\n\n"
        f"英文標題：{title}\n"
        f"英文摘要：{summary}\n"
        f"請用JSON格式回覆，包含以下欄位：\n"
        f"{{\"title_zh\": \"中文標題\", \"summary_zh\": \"中文摘要\", \"applications\": [\"應用場景1\", \"應用場景2\", \"應用場景3\"], \"pitch\": \"向創投推銷的內容\"}}"
    )
    response = model.generate_content(prompt)
    text = response.text.strip()
    # 移除可能的 markdown 程式碼區塊標記
    text = re.sub(r"^```json|^```|```$", "", text, flags=re.MULTILINE).strip()
    # 解析 JSON 回應
    result = json.loads(text)
    return result

# === 將摘要轉成語音檔 ===
def save_audio(text, filename):
    tts = gTTS(text, lang='zh-tw')
    tts.save(filename)

# === 主流程 ===
def main():
    os.makedirs("audios", exist_ok=True)

    # 抓取所有 QUERY 文章
    papers = []
    for query in QUERY:
        print(f"正在抓取 {query} 相關文章...")
        result = fetch_ai_papers(query)
        if result:
            papers.extend(result)
            print(f"已抓取:{papers[-1]['title']}")
    print(f"總共抓取到 {len(papers)} 篇文章")
    
    # 無文章則無更新
    if len(papers) == 0:
        print("沒有抓到任何文章，無更新")
        return
      # 處理每篇論文
    for i, paper in enumerate(papers):
        # 翻譯
        print(f"正在處理第 {i+1} 篇 {paper['title']}")
        result = summarize_to_chinese(paper['title'], paper['summary'])
        
        # 組合音訊內容：標題、摘要、應用場景與創投推銷點
        audio_content = (
            f"{result['title_zh']}\n\n"
            f"{result['summary_zh']}\n\n"
            f"這項技術有三個生活化的應用場景：\n"
            f"第一，{result['applications'][0]}\n"
            f"第二，{result['applications'][1]}\n" 
            f"第三，{result['applications'][2]}\n\n"
            f"如果向創投或天使基金推銷，可以這樣說：\n{result['pitch']}"
        )
        
        # 生成音訊檔
        audio_path = f"audios/{paper['id']}.mp3"
        save_audio(audio_content, audio_path)

        # 更新json資料
        paper_data = paper.copy()  # 複製原始資料
        paper_data.update({
            "title_zh": result['title_zh'],
            "summary_zh": result['summary_zh'],
            "applications": result['applications'],
            "pitch": result['pitch'],
            "audio": audio_path,
            "timestamp": datetime.now().isoformat()
        })
        
        # 直接將新文章附加到檔案末尾
        with open(NEWS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(paper_data, ensure_ascii=False) + "\n")

    print("✅ 更新完成：news.jsonl 和 MP3 音檔已產生")

if __name__ == "__main__":
    main()

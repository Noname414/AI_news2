# AI新聞更新系統 - 部署指南

## 🚀 部署概述

本指南介紹如何在不同環境中部署 AI 新聞更新系統。

## 📋 系統要求

### 最低要求
- Python 3.8+
- 8GB RAM
- 10GB 可用磁盤空間
- 穩定的網絡連接

### 推薦配置
- Python 3.11+
- 16GB RAM
- 50GB 可用磁盤空間
- SSD 存儲
- 多核 CPU

## 🔧 環境配置

### 1. 系統依賴

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
sudo apt install -y sqlite3 libsqlite3-dev
sudo apt install -y ffmpeg  # 音頻處理
```

**CentOS/RHEL:**
```bash
sudo yum update -y
sudo yum install -y python3 python3-pip git
sudo yum install -y sqlite sqlite-devel
sudo yum install -y ffmpeg
```

**macOS:**
```bash
brew install python3 git sqlite3 ffmpeg
```

**Windows:**
- 安裝 Python 3.11+ 從 [python.org](https://python.org)
- 安裝 Git 從 [git-scm.com](https://git-scm.com)
- 安裝 FFmpeg 從 [ffmpeg.org](https://ffmpeg.org)

### 2. 項目設置

```bash
# 克隆項目
git clone <your-repo-url>
cd AI_news2

# 創建虛擬環境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt
```

### 3. 環境變量

創建 `.env` 文件：
```bash
# API 配置
GEMINI_API_KEY=your_gemini_api_key_here

# 可選：數據庫配置
DATABASE_URL=sqlite:///news.db

# 可選：日誌級別
LOG_LEVEL=INFO

# 可選：文件路徑
AUDIO_DIR=./audios
LOG_DIR=./logs
```

## 🐳 Docker 部署

### Dockerfile
```dockerfile
FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    sqlite3 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 創建必要目錄
RUN mkdir -p audios logs

# 設置環境變量
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# 暴露端口（如果有 web 界面）
EXPOSE 8000

# 啟動命令
CMD ["python", "cli.py", "run"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  ai-news:
    build: .
    container_name: ai-news-updater
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DATABASE_URL=sqlite:///data/news.db
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./audios:/app/audios
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml
    restart: unless-stopped
    networks:
      - ai-news-network

  # 可選：監控服務
  monitoring:
    image: prom/prometheus:latest
    container_name: ai-news-monitoring
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - ai-news-network

networks:
  ai-news-network:
    driver: bridge
```

### 部署命令
```bash
# 構建並啟動
docker-compose up -d

# 查看日誌
docker-compose logs -f ai-news

# 停止服務
docker-compose down
```

## 🔄 系統服務（Linux）

### Systemd 服務文件

創建 `/etc/systemd/system/ai-news.service`：
```ini
[Unit]
Description=AI News Updater Service
After=network.target

[Service]
Type=simple
User=ai-news
Group=ai-news
WorkingDirectory=/opt/ai-news
Environment=PATH=/opt/ai-news/venv/bin
ExecStart=/opt/ai-news/venv/bin/python cli.py run --daemon
Restart=always
RestartSec=10

# 環境變量
Environment=GEMINI_API_KEY=your_api_key_here
Environment=LOG_LEVEL=INFO

# 資源限制
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

### 服務管理命令
```bash
# 啟用服務
sudo systemctl enable ai-news
sudo systemctl start ai-news

# 檢查狀態
sudo systemctl status ai-news

# 查看日誌
sudo journalctl -u ai-news -f

# 重啟服務
sudo systemctl restart ai-news
```

## 📈 監控和日誌

### 日誌配置

在 `config.yaml` 中配置：
```yaml
logging:
  level: INFO
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file_handler:
    enabled: true
    max_bytes: 10485760  # 10MB
    backup_count: 5
  syslog:
    enabled: true  # 生產環境建議啟用
    facility: 'local0'
```

### 監控設置

使用內建監控工具：
```bash
# 實時監控
python cli.py monitor

# 檢查系統健康
python cli.py status

# 查看數據庫統計
python cli.py db stats
```

### Prometheus 監控（可選）

創建 `monitoring/prometheus.yml`：
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-news'
    static_configs:
      - targets: ['ai-news:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

## 🔐 安全配置

### 1. API 密鑰管理
```bash
# 使用環境變量
export GEMINI_API_KEY="your_secure_api_key"

# 或使用密鑰管理服務
# AWS Secrets Manager, Azure Key Vault 等
```

### 2. 文件權限
```bash
# 設置適當的文件權限
chmod 600 config.yaml  # 配置文件
chmod 700 logs/         # 日誌目錄
chmod 755 audios/       # 音頻文件目錄
```

### 3. 防火牆設置
```bash
# 僅允許必要的端口
sudo ufw allow ssh
sudo ufw allow 8000/tcp  # 如果有 web 界面
sudo ufw enable
```

## 📊 性能調優

### 1. 數據庫優化

**SQLite 配置:**
```python
# 在 config.yaml 中
database:
  url: "sqlite:///news.db?check_same_thread=False"
  echo: false
  pool_pre_ping: true
  connect_args:
    timeout: 30
    isolation_level: null
```

**PostgreSQL 配置（生產環境推薦）:**
```yaml
database:
  url: "postgresql://user:password@localhost/ai_news"
  pool_size: 10
  max_overflow: 20
```

### 2. 並發設置
```yaml
concurrency:
  max_workers: 4  # 根據 CPU 核心數調整
  semaphore_limit: 8
  batch_size: 10
```

### 3. 緩存配置
```yaml
cache:
  enabled: true
  ttl: 3600  # 1小時
  max_size: 1000
```

## 🚨 故障排除

### 常見問題

1. **內存不足**
   - 減少 `max_workers`
   - 增加系統內存
   - 啟用磁盤交換

2. **API 限制**
   - 調整 `rate_limit` 設置
   - 增加重試延遲
   - 檢查 API 配額

3. **磁盤空間不足**
   - 清理舊音頻文件
   - 設置日誌輪轉
   - 壓縮歷史數據

### 日誌分析
```bash
# 檢查錯誤日誌
grep ERROR logs/ai_news.log

# 分析性能
grep "Processing time" logs/ai_news.log

# 監控 API 調用
grep "API call" logs/ai_news.log
```

## 🔄 備份和恢復

### 數據備份
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/ai-news"

# 創建備份目錄
mkdir -p $BACKUP_DIR

# 備份數據庫
cp news.db $BACKUP_DIR/news_$DATE.db

# 備份配置
cp config.yaml $BACKUP_DIR/config_$DATE.yaml

# 備份音頻文件（可選）
tar -czf $BACKUP_DIR/audios_$DATE.tar.gz audios/

# 清理舊備份（保留30天）
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### 自動備份（crontab）
```bash
# 每天凌晨2點備份
0 2 * * * /opt/ai-news/backup.sh
```

## 📈 擴展性

### 水平擴展
- 使用消息隊列（Redis/RabbitMQ）
- 微服務架構
- 負載均衡器

### 垂直擴展
- 增加 CPU 核心數
- 增加內存容量
- 使用 SSD 存儲

## 🔗 相關資源

- [項目文檔](README_v2.md)
- [API 文檔](docs/api.md)
- [故障排除指南](docs/troubleshooting.md)
- [性能調優指南](docs/performance.md)

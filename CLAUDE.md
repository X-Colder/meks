# MEKS - 医疗专家知识库系统

## 快速开始

### 环境要求
- Docker & Docker Compose
- Python 3.11+ (本地开发)
- Node.js 20+ (本地开发)

### 一键启动

```bash
cp .env.example .env
docker compose up -d
```

### 本地开发

**后端:**
```bash
cd backend
uv pip install -e ".[dev]"
uvicorn meks.main:app --reload
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

### 初始化

```bash
# 运行数据库迁移
cd backend && alembic upgrade head

# 创建管理员账号
python scripts/seed_admin.py
```

默认管理员: `admin` / `admin123456`

## 架构

- **后端**: Python FastAPI + SQLAlchemy + Celery
- **前端**: React + TypeScript + Ant Design
- **向量库**: Milvus
- **存储**: PostgreSQL + MinIO + Redis
- **AI**: Ollama (本地) + Cloud API (可选)

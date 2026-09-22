# 灵犀（LinguaLearner）— 项目初始化指南

**日期**：2026-08-09
**基于**：产品需求规格书 v1.0 + 技术架构设计 v1.0

> 整份指南分 4 步走完：环境检查 → 前端脚手架 → 后端脚手架 → Docker 全家桶拉起来。


## 1. 开发环境配置

### 1.1 必备软件

| 软件             | 最低版本  | 验证命令               | 用途                       |
| -------------- | ----- | ------------------ | ------------------------ |
| Node.js        | 22.x  | `node --version`   | 前端运行时                    |
| pnpm           | 9.x   | `pnpm --version`   | 前端包管理（比 npm 快、磁盘省）       |
| Python         | 3.12+ | `python --version` | 后端运行时                    |
| Poetry         | 1.8+  | `poetry --version` | Python 依赖管理（替代 pip+venv） |
| Docker Desktop | 26+   | `docker --version` | 本地基础设施（PG/Redis/MinIO）   |
| Git            | 2.40+ | `git --version`    | 版本控制                     |

```bash file:环境检查
echo "=== 环境检查 ==="
echo "Node.js: $(node --version)"
echo "pnpm:   $(pnpm --version)"
echo "Python: $(python3 --version 2>&1)"
echo "Poetry: $(poetry --version 2>&1)"
echo "Docker: $(docker --version 2>&1)"
echo "Git:    $(git --version)"
echo "Docker Compose: $(docker compose version 2>&1)"
```

> 本机：node v24.14.0；pnpm 10.32.1；docker 28.4.0；git 2.52.0


## 2. 项目目录搭建

```file:基于架构文档第5章
lingua-learner/                    # 项目根目录
│
├── frontend/                      # React PWA — Vite + TypeScript
│   ├── public/                    # 静态资源（favicon、PWA manifest 图标）
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/               # Radix UI 二次封装（Button/Dialog/Select...）
│   │   │   ├── dashboard/        # 仪表盘组件
│   │   │   ├── capture/          # 内容捕获组件
│   │   │   ├── chat/             # AI 对话组件
│   │   │   ├── digital-human/    # 桌面数字人组件（VRM渲染/Lip-Sync/表情/悬浮窗）
│   │   │   └── memory/           # 复习卡片组件
│   │   ├── hooks/                # 自定义 hooks
│   │   ├── stores/               # Zustand stores
│   │   ├── services/             # API 调用层（axios 封装）
│   │   ├── lib/                  # 工具函数
│   │   ├── pages/                # 路由页面
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py           # 依赖注入（get_db, get_current_user）
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── capture.py
│   │   │       ├── memory.py
│   │   │       ├── chat.py
│   │   │       ├── digital_human.py
│   │   │       ├── dashboard.py
│   │   │       └── path.py
│   │   ├── core/
│   │   │   ├── config.py         # pydantic-settings 配置管理
│   │   │   ├── security.py       # JWT + bcrypt
│   │   │   └── database.py       # async SQLAlchemy 连接池
│   │   ├── models/               # SQLAlchemy ORM
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── capture.py
│   │   │   ├── card.py
│   │   │   ├── concept.py
│   │   │   ├── chat.py
│   │   │   ├── digital_human.py
│   │   │   └── event.py
│   │   ├── schemas/              # Pydantic v2 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── capture.py
│   │   │   ├── memory.py
│   │   │   ├── chat.py
│   │   │   ├── digital_human.py
│   │   │   ├── dashboard.py
│   │   │   └── path.py
│   │   ├── services/             # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── capture_service.py
│   │   │   ├── memory_service.py
│   │   │   ├── fsrs_engine.py
│   │   │   ├── chat_service.py
│   │   │   ├── digital_human_service.py
│   │   │   ├── dashboard_service.py
│   │   │   ├── path_service.py
│   │   │   └── concept_graph_service.py
│   │   ├── ai/                   # AI 能力封装
│   │   │   ├── __init__.py
│   │   │   ├── llm.py
│   │   │   ├── embedding.py
│   │   │   ├── stt.py
│   │   │   ├── tts.py
│   │   │   └── cost_tracker.py
│   │   ├── workers/              # Celery 异步任务
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py     # Celery 实例 + 配置
│   │   │   ├── extract_concepts.py
│   │   │   ├── generate_cards.py
│   │   │   ├── build_queue.py
│   │   │   ├── daily_digest.py
│   │   │   └── update_graph.py
│   │   └── main.py               # FastAPI 入口
│   ├── alembic/                  # DB 迁移（alembic init 生成）
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── tests/                    # 测试
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_capture.py
│   │   └── test_memory.py
│   ├── pyproject.toml            # Poetry 配置
│   ├── Dockerfile
│   └── .env.example              # 环境变量模板
│
├── docker/                        # Docker 相关配置
│   ├── nginx/
│   │   └── default.conf          # Nginx 反向代理配置（开发阶段可选）
│   └── postgres/
│       └── init.sql              # 初始化 SQL（创建 pgvector 扩展等）
│
├── .github/
│   └── workflows/
│       ├── ci-frontend.yml       # 前端 CI
│       └── ci-backend.yml        # 后端 CI
│
├── docker-compose.yml            # 本地开发环境
├── docker-compose.prod.yml       # 生产部署（MVP 阶段同一套，后续拆）
├── .gitignore
├── .editorconfig
└── README.md
```

> 项目脚手架搭建 —— 逐步命令——以下命令在项目根目录 `lingua-learner/` 下执行。

### 阶段一：创建项目根目录 + Git 初始化

```bash
mkdir lingua-learner && cd lingua-learner
git init

# 根目录 .gitignore
cat > .gitignore << 'EOF'
# Dependencies
node_modules/
.pnpm-store/

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
dist/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
docker-data/

# OS
.DS_Store
Thumbs.db

# Build output
frontend/dist/
EOF

# EditorConfig（统一缩进风格）
cat > .editorconfig << 'EOF'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.{ts,tsx,js,jsx,json}]
indent_style = space
indent_size = 2

[*.py]
indent_style = space
indent_size = 4

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[Makefile]
indent_style = tab
EOF
```

---

### 阶段二：前端项目 — Vite + React + TypeScript + Tailwind

```bash
# 用 Vite 官方脚手架创建
pnpm create vite frontend --template react-ts
cd frontend

# 安装核心依赖
pnpm add react-router-dom@6 @tanstack/react-query zustand axios

# 安装 UI 框架
pnpm add tailwindcss @tailwindcss/vite postcss @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select @radix-ui/react-tabs @radix-ui/react-tooltip

# 安装工具库
pnpm add clsx tailwind-merge date-fns lucide-react

# 安装数字人相关依赖（Three.js + VRM）
pnpm add three @pixiv/three-vrm
pnpm add -D @types/three

# 安装 PWA 支持
pnpm add -D vite-plugin-pwa workbox-window

# 初始化 Tailwind（Vite + Tailwind v4 方式）
# Tailwind v4 使用 CSS-first 配置，不需要 tailwind.config.ts
# 编辑 src/index.css 加入 @import "tailwindcss";

cd ..
```

**关键配置文件的初始内容**：

`frontend/vite.config.ts`（替换默认内容）：
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png'],
      manifest: {
        name: '灵犀 LinguaLearner',
        short_name: '灵犀',
        description: '全领域AI学习伙伴',
        theme_color: '#6366f1',       // Indigo-500
        background_color: '#0f172a',  // Slate-900
        display: 'standalone',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^\/api\/.*/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

`frontend/src/index.css`（替换默认内容）：
```css
@import "tailwindcss";

/* 自定义 CSS 变量（品牌色） */
:root {
  --color-primary: #6366f1;     /* Indigo-500 */
  --color-primary-dark: #4f46e5;/* Indigo-600 */
  --color-success: #22c55e;     /* Green-500 */
  --color-warning: #f59e0b;     /* Amber-500 */
  --color-danger: #ef4444;      /* Red-500 */
}

body {
  @apply bg-slate-950 text-slate-100 antialiased;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* 滚动条美化 */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { @apply bg-slate-700 rounded-full; }
::-webkit-scrollbar-thumb:hover { @apply bg-slate-600; }
```

---

### 阶段三：后端项目 — FastAPI + Poetry

```bash
cd lingua-learner    # 回到项目根目录

# 用 Poetry 初始化 Python 项目
poetry new backend --name app
cd backend

# 或者如果 poetry new 创建了你不想要的结构，手动创建目录更干净：
# （如果用 poetry new，它会创建 src/app/ 结构，我们把内容放到 app/ 下即可）

# 安装核心依赖
poetry add fastapi[standard] uvicorn[standard] pydantic-settings
poetry add sqlalchemy[asyncio] asyncpg alembic psycopg2-binary
poetry add pgvector                     # pgvector Python 客户端
poetry add python-jose[cryptography] passlib[bcrypt] python-multipart
poetry add redis celery[redis]
poetry add openai httpx python-dotenv
poetry add pydantic                     # v2 已默认包含

# 安装开发依赖
poetry add -G dev pytest pytest-asyncio httpx black ruff mypy

# 安装 fsrs-py（间隔重复算法）
poetry add fsrs-py

cd ..
```

**关键配置文件**：

`backend/.env.example`：
```ini
# ========== 应用 ==========
APP_NAME=灵犀 LinguaLearner
APP_ENV=development
DEBUG=true
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
API_V1_PREFIX=/api/v1

# ========== 数据库 ==========
DATABASE_URL=postgresql+asyncpg://lingua:lingua_dev@localhost:5432/lingua_dev
DATABASE_URL_SYNC=postgresql://lingua:lingua_dev@localhost:5432/lingua_dev

# ========== Redis ==========
REDIS_URL=redis://localhost:6379/0

# ========== AI ==========
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# 可选备选模型
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# ========== JWT ==========
JWT_SECRET_KEY=change-me-to-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ========== 存储 ==========
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=lingua-learner

# ========== AI 成本控制 ==========
DAILY_TOKEN_BUDGET_GPT4O=10000
DAILY_TOKEN_BUDGET_EMBEDDING=50000
```

`backend/app/core/config.py`（骨架）：
```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    app_name: str = "灵犀 LinguaLearner"
    app_env: str = "development"
    debug: bool = True
    secret_key: str
    api_v1_prefix: str = "/api/v1"

    # 数据库
    database_url: str
    database_url_sync: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    anthropic_api_key: str | None = None
    claude_model: str = "claude-3-5-sonnet-20241022"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # 存储
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "lingua-learner"

    # AI 成本控制
    daily_token_budget_gpt4o: int = 10000
    daily_token_budget_embedding: int = 50000

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/app/main.py`（入口骨架）：
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化连接池、加载模型
    yield
    # 关闭时：释放连接


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS（开发阶段放开，生产收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
```

---

### 阶段四：Docker 全家桶 — 本地开发基础设施

```bash
cd lingua-learner    # 项目根目录

# 创建 docker 相关目录
mkdir -p docker/postgres docker/nginx
```

`docker-compose.yml`（本地开发环境）：
```yaml
version: "3.9"

services:
  # ====== PostgreSQL 15 + pgvector ======
  postgres:
    image: pgvector/pgvector:pg15
    container_name: lingua-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: lingua
      POSTGRES_PASSWORD: lingua_dev
      POSTGRES_DB: lingua_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lingua -d lingua_dev"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ====== Redis 7 ======
  redis:
    image: redis:7-alpine
    container_name: lingua-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ====== MinIO（对象存储） ======
  minio:
    image: minio/minio:latest
    container_name: lingua-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"    # API
      - "9001:9001"    # Web Console
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ====== 创建 MinIO Bucket（一次性） ======
  minio-create-bucket:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 minioadmin minioadmin;
      mc mb local/lingua-learner --ignore-existing;
      mc anonymous set download local/lingua-learner;
      echo 'MinIO bucket ready';
      exit 0;
      "

volumes:
  pgdata:
  redisdata:
  miniodata:
```

`docker/postgres/init.sql`：
```sql
-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 验证扩展安装
SELECT extname, extversion FROM pg_extension;
```

`docker/nginx/default.conf`（生产部署时用，开发阶段可暂不配置）：
```nginx
server {
    listen 80;
    server_name localhost;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

---

### 阶段五：GitHub Actions CI 骨架

```bash
mkdir -p .github/workflows
```

`.github/workflows/ci-frontend.yml`：
```yaml
name: CI - Frontend

on:
  push:
    paths: ['frontend/**']
  pull_request:
    paths: ['frontend/**']

jobs:
  lint-and-build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'pnpm'
          cache-dependency-path: frontend/pnpm-lock.yaml

      - run: pnpm install --frozen-lockfile
      - run: pnpm run lint
      - run: pnpm run build
      - run: pnpm run typecheck
```

`.github/workflows/ci-backend.yml`：
```yaml
name: CI - Backend

on:
  push:
    paths: ['backend/**']
  pull_request:
    paths: ['backend/**']

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_USER: lingua_test
          POSTGRES_PASSWORD: lingua_test
          POSTGRES_DB: lingua_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U lingua_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Poetry
        run: pipx install poetry

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'poetry'

      - run: poetry install

      - name: Lint (ruff)
        run: poetry run ruff check app/

      - name: Type check (mypy)
        run: poetry run mypy app/

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://lingua_test:lingua_test@localhost:5432/lingua_test
          REDIS_URL: redis://localhost:6379/0
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SECRET_KEY: test-secret-key
          JWT_SECRET_KEY: test-jwt-secret-key
        run: poetry run pytest -v --cov=app --cov-report=xml
```

---

## 4. 一键启动开发环境

在项目根目录 `lingua-learner/` 下执行：

```bash
# ====== 第一次启动 ======

# 1. 拉取并启动 Docker 基础设施（PostgreSQL + Redis + MinIO）
docker compose up -d

# 2. 等待服务就绪（约 15-30 秒）
echo "Waiting for services..."
sleep 15

# 3. 验证基础设施
docker compose ps           # 应该看到 3 个服务 running
curl http://localhost:5432  # 应该返回空响应（PG 端口）
curl http://localhost:9001  # MinIO Web Console

# 4. 初始化后端
cd backend
cp .env.example .env        # 复制环境变量模板
# ⚠️ 编辑 .env，填入真实的 OPENAI_API_KEY

# 创建 venv + 安装依赖
poetry install

# 初始化 Alembic（数据库迁移）
poetry run alembic init alembic

# 生成初始迁移
poetry run alembic revision --autogenerate -m "init"
poetry run alembic upgrade head

# 启动后端（开发模式，热重载）
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 另开一个终端，启动前端
cd ../frontend
pnpm install
pnpm run dev                # 浏览器访问 http://localhost:5173
```

**验证后端**：
- API 文档：http://localhost:8000/docs（FastAPI 自动生成的 Swagger UI）
- 健康检查：http://localhost:8000/health

---

## 5. 目录创建脚本（一次性创建所有空目录 + `__init__.py`）

不想手动一个个 `mkdir`？在项目根目录运行这个：

```bash
# ====== 后端目录结构 ======
mkdir -p backend/app/{api/v1,core,models,schemas,services,ai,workers}
mkdir -p backend/alembic/versions
mkdir -p backend/tests

# 创建所有 __init__.py
find backend/app -type d -exec touch {}/__init__.py \;

# ====== 前端目录结构 ======
mkdir -p frontend/src/{components/{ui,dashboard,capture,chat,digital-human,memory},hooks,stores,services,lib,pages}

# ====== Docker + CI ======
mkdir -p docker/{postgres,nginx}
mkdir -p .github/workflows
```

---

## 6. 开发工作流速查

```bash
# ====== 前端 ======
cd frontend
pnpm dev              # 启动开发服务器
pnpm build            # 生产构建
pnpm lint             # ESLint 检查
pnpm typecheck        # TypeScript 类型检查

# ====== 后端 ======
cd backend
poetry run uvicorn app.main:app --reload   # 开发服务器
poetry run pytest -v                       # 运行测试
poetry run ruff check app/                 # Lint 检查
poetry run mypy app/                       # 类型检查
poetry run alembic upgrade head            # 执行数据库迁移
poetry run alembic revision --autogenerate -m "描述"  # 生成迁移

# ====== Docker ======
docker compose up -d     # 启动所有基础设施
docker compose down      # 停止
docker compose logs -f   # 查看日志
docker compose ps        # 查看状态
```

---

## 7. 待确认事项（阻塞下一步）

在正式开始写业务代码之前，需要团队决策的几件事：

| # | 问题 | 阻塞什么 | 建议 |
|---|------|---------|------|
| 1 | **项目代码托管在哪？** GitHub / GitLab / 私有 Git？ | Git remote + CI 配置 | GitHub（CI 模板已基于 GitHub Actions 写） |
| 2 | **OPENAI_API_KEY 怎么管理？** 个人账号还是团队账号？ | 后端无法调用 AI | 开发阶段先用个人 key；生产用环境变量注入 |
| 3 | **前端路由设计**：几个页面？页面间怎么跳转？ | 前端 pages 目录和路由配置 | 建议首页 = Dashboard、/capture、/chat、/memory、/path |
| 4 | **是否需要先跑 M1 三个 Spike？**（STT/TTS 选型、FSRS 评估、PWA 录音 POC） | 对话模块和记忆模块的实现方式 | PRD 标注 W1-3 必须完成，可以先用 mock 数据搭脚手架并行进行 |
| 5 | **数据库 ORM 建模**：是先画完所有模型的 ER 图再迁移，还是边写边改？ | Alembic 迁移策略 | 建议先建核心表（User/Capture/Card/Concept），M2 再加 Chat/Dashboard 表 |
| 6 | **数字人 VRM 模型来源？** 使用 VRoid Hub 免费模型还是自制？ | P1-6 数字人模块开发 | 建议初期用 VRoid Hub 免费可商用模型，3-5 个角色供用户选择 |
| 7 | **数字人语音交互优先级**：Web Speech API 先行还是直接上 Whisper？ | P1-6 STT 方案选型 | 建议 Web Speech API 优先（零成本零延迟），Spike D 验证效果后决定回退策略 |

---

## 附录：package.json scripts 推荐

`frontend/package.json` 中建议的 scripts：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "typecheck": "tsc --noEmit",
    "format": "prettier --write \"src/**/*.{ts,tsx,css,json}\""
  }
}
```

---

> 以上是灵犀项目"从零到能跑"的完整初始化指南。环境搭好后，Swagger UI 能看到空 API 列表、前端能看到空白的 Vite 页面，就是脚手架就绪的信号。接下来按 M1 里程碑——先做 P0-1（内容捕获）和 P0-5（学习路径）的业务代码。

```file:后端脚手架
# ====== 1. 创建 Conda 环境 ======
conda create --name learner python=3.12 -y
conda activate learner
pip install poetry==1.8.3

# 验证
python --version
poetry --version

# 让 Poetry 直接用当前 conda 环境，不再自己建 venv
poetry config virtualenvs.create false

# ====== 2. 创建项目根目录 + Git 初始化 ======
mkdir lingua-learner && cd lingua-learner
git init

# ====== 3. 用 Poetry 创建 backend 包（会自动生成 pyproject.toml + app/ + tests/） ======
poetry new backend --name app
cd backend
# 注意：poetry new 已经生成了 pyproject.toml，之后不要再运行 poetry init

# ====== 4. 补全 app/ 内部子目录结构 ======
# Windows cmd 下逐条 mkdir（不支持 mkdir -p app/{a,b,c} 的大括号展开）；
# 若用 Git Bash 则可以用 mkdir -p app/{api/v1,core,models,schemas,services,ai,workers}
mkdir app\api\v1
mkdir app\core
mkdir app\models
mkdir app\schemas
mkdir app\services
mkdir app\ai
mkdir app\workers
mkdir alembic\versions

# 建各目录的 __init__.py（Git Bash 下可用 find app -type d -exec touch {}/__init__.py \;）
type nul > app\__init__.py
type nul > app\api\__init__.py
type nul > app\api\v1\__init__.py
type nul > app\core\__init__.py
type nul > app\models\__init__.py
type nul > app\schemas\__init__.py
type nul > app\services\__init__.py
type nul > app\ai\__init__.py
type nul > app\workers\__init__.py

# ====== 5. 安装依赖 ======
poetry add fastapi[standard] uvicorn[standard] pydantic-settings
poetry add sqlalchemy[asyncio] asyncpg alembic psycopg2-binary
poetry add pgvector
poetry add python-jose[cryptography] passlib[bcrypt] python-multipart
poetry add openai httpx python-dotenv

# 注意：不要单独指定 redis 版本再加 celery[redis]，会导致版本冲突
# （celery 5.6.3 要求 redis<6.5，但单独 poetry add redis 会拿到不兼容的最新版）
# 直接用 celery[redis]，让它自己解析出兼容的 redis 版本
poetry add "celery[redis]^5.6"

# 开发依赖
poetry add -G dev pytest pytest-asyncio httpx black ruff mypy

# 间隔重复算法库：PyPI 上的包名是 fsrs（不是 fsrs-py，那是 GitHub 仓库名）
poetry add fsrs

# ====== 6. 创建关键骨架文件 ======
# backend/.env.example      —— 环境变量模板，列出所有需要配置的变量（数据库/Redis/OpenAI/JWT等）
# backend/app/core/config.py —— 用 pydantic-settings 把 .env 里的变量加载成有类型的配置对象
# backend/app/main.py        —— FastAPI 应用入口，创建 app、挂 CORS、提供 /health 健康检查接口
# 三个文件内容见"技术架构设计"/"项目初始化指南"文档，或让 AI 助手按指南内容生成

# ====== 7. 复制环境变量文件并填入真实值 ======
copy .env.example .env
# 编辑 .env，至少填入：
#   SECRET_KEY / JWT_SECRET_KEY —— 先随便填一个随机字符串占位，生产环境用 openssl rand -hex 32 生成
#   OPENAI_API_KEY              —— 真实 key，没有的话先占位，不影响 /health 验证
#   DATABASE_URL / REDIS_URL    —— 先保持默认值，等 Docker 基础设施起来后自然匹配

# ====== 8. 启动后端验证 ======
poetry run uvicorn app.main:app --reload

# 验证：
#   浏览器访问 http://localhost:8000/health   应返回 {"status":"ok","app":"灵犀 LinguaLearner"}
#   浏览器访问 http://localhost:8000/docs     应看到 FastAPI 自动生成的 Swagger 文档（暂时是空的）
```

```file:前端脚手架
# ====== 1. 验证环境 ======
node --version   # 需 22.x+
pnpm --version    # 需 9.x+

# ====== 2. 用 Vite 脚手架创建项目 ======
cd E:\pySpace\lingua-learner
pnpm create vite frontend --template react-ts
# 交互式提问：
#   Which linter to use?          -> 选 ESLint（不选 Oxlint，和后面的 package.json scripts 保持一致）
#   Install with pnpm and start now? -> 选 Yes（自动装依赖并跑起来，跑起来后先 Ctrl+C 停掉，继续装依赖）

cd frontend

# ====== 3. 安装核心依赖 ======
# 路由 + 请求缓存/状态管理 + HTTP 客户端
pnpm add react-router-dom@6 @tanstack/react-query zustand axios

# UI 框架：Tailwind v4（CSS-first，不需要 tailwind.config.ts） + Radix UI 无样式组件
pnpm add tailwindcss @tailwindcss/vite postcss @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select @radix-ui/react-tabs @radix-ui/react-tooltip

# 工具库：className 合并、日期处理、图标
pnpm add clsx tailwind-merge date-fns lucide-react

# 数字人模块依赖：Three.js 渲染引擎 + VRM 模型加载
pnpm add three @pixiv/three-vrm
pnpm add -D @types/three

# PWA 支持：离线缓存、manifest 生成
pnpm add -D vite-plugin-pwa workbox-window

# ====== 4. 修改默认配置文件 ======

# 4.1 vite.config.ts —— 替换默认内容
#     目的：接入 Tailwind 插件、接入 PWA 插件（离线缓存策略、应用 manifest）、
#          配置开发代理（/api 转发到后端 8000 端口，/ws 走 WebSocket 代理），
#          这样前端 fetch('/api/xxx') 时不用写后端完整地址，也不会有跨域问题
#     内容见"项目初始化指南"文档「阶段二」或让 AI 助手生成

# 4.2 src/index.css —— 替换默认内容
#     目的：Vite 脚手架默认生成的是一套演示样式（带 :root 变量、#root 布局等），
#          换成 Tailwind v4 的 CSS-first 引入方式（@import "tailwindcss";）+ 品牌色 CSS 变量
#          + 深色背景基础样式 + 滚动条美化
#     内容见"项目初始化指南"文档「阶段二」

# 4.3 src/App.tsx —— 替换默认内容
#     目的：Vite 脚手架默认生成的是一个带计数器和文档链接的演示页面，
#          清空换成占位页面，等业务页面路由搭好后再逐步替换
#     删除 src/App.css（不再被引用的默认样式文件）

# ====== 5. 创建业务目录结构 ======
# Windows cmd 下逐条 mkdir；Git Bash 下可用 mkdir -p 的大括号展开一次性建好
cd src
mkdir components\ui
mkdir components\dashboard
mkdir components\capture
mkdir components\chat
mkdir components\digital-human
mkdir components\memory
mkdir hooks
mkdir stores
mkdir services
mkdir lib
mkdir pages
cd ..

# 各目录用途：
#   components/ui           —— Radix UI 二次封装（Button/Dialog/Select...）
#   components/dashboard     —— 仪表盘组件
#   components/capture       —— 内容捕获组件
#   components/chat          —— AI 对话组件
#   components/digital-human —— 桌面数字人组件（VRM渲染/Lip-Sync/表情/悬浮窗）
#   components/memory        —— 复习卡片组件
#   hooks                    —— 自定义 hooks
#   stores                   —— Zustand stores
#   services                —— API 调用层（axios 封装）
#   lib                      —— 工具函数
#   pages                    —— 路由页面

# ====== 6. package.json 补充 scripts ======
# 在 scripts 里追加一条：
#   "typecheck": "tsc --noEmit"
# 目的：单独跑 TypeScript 类型检查，不依赖 build 流程，CI 里也会用到
# （"format": "prettier --write ..." 暂不加，因为还没装 prettier，避免脚本指向不存在的工具）

# ====== 7. 验证 ======
pnpm run typecheck   # 应无报错，说明配置文件类型正确
pnpm run dev          # 启动开发服务器
# 浏览器访问 http://localhost:5173  应看到深色背景 + "灵犀 LinguaLearner" 靛蓝色标题
# 确认 Tailwind、PWA 插件都正常生效（终端无报错）
```

```file:Docker 基础设施的准备
# ====== 1. 验证 Docker 环境 ======
docker --version          # 需 26+
docker compose version

# ====== 2. 创建 Docker 相关目录 ======
cd E:\pySpace\lingua-learner
mkdir docker\postgres
mkdir docker\nginx

# ====== 3. 创建 docker-compose.yml（项目根目录） ======
# 三个服务 + 一个一次性任务：
#   postgres              —— pgvector/pgvector:pg15 镜像（带向量扩展的 PG15），映射 5432
#   redis                  —— redis:7-alpine，映射 6379
#   minio                  —— 对象存储，映射 9000（API）/9001（Web 控制台），账号密码 minioadmin/minioadmin
#   minio-create-bucket    —— 一次性任务，等 minio healthy 后自动创建 lingua-learner bucket 并设置下载权限
# 注意：不要写 `version: "3.9"` 这行，新版 Docker Compose 已废弃该字段，写了会一直报 warning
# 内容见"项目初始化指南"文档「阶段四」或让 AI 助手生成

# ====== 4. 创建 docker/postgres/init.sql ======
# 目的：容器首次启动时自动执行，给数据库开启两个扩展：
#   vector      —— pgvector，支持向量存储和相似度检索（后续做 AI 语义搜索用）
#   uuid-ossp   —— 支持生成 UUID 主键
# 内容：
#   CREATE EXTENSION IF NOT EXISTS vector;
#   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
#   SELECT extname, extversion FROM pg_extension;

# ====== 5. 启动 ======
docker compose up -d
# 首次启动会拉取镜像，可能耗时较久；若中途网络中断报 "short read: unexpected EOF"，
# 重新执行 docker compose up -d 即可（已下载的层不会丢失，会自动续传）
# 若反复失败，可以先单独逐个拉镜像再启动：
#   docker pull pgvector/pgvector:pg15
#   docker pull redis:7-alpine
#   docker pull minio/minio:latest
#   docker pull minio/mc:latest

# ====== 6. 验证 ======
docker compose ps
# 期望：postgres / redis / minio 三个服务状态都是 healthy
# （minio-create-bucket 是一次性任务，执行完会退出，ps 默认不显示它，这是正常的）

# 验证 pgvector 扩展是否装好：
docker exec lingua-postgres psql -U lingua -d lingua_dev -c "SELECT extname, extversion FROM pg_extension;"
# 应看到 vector 和 uuid-ossp 都在列表里

# 验证 MinIO bucket 是否创建成功：
docker compose logs minio-create-bucket
# 应看到 "Bucket created successfully `local/lingua-learner`" 和 "MinIO bucket ready"

# 浏览器验证（可选）：
#   http://localhost:9001   MinIO Web 控制台，账号密码 minioadmin/minioadmin

# ====== 7. 常用管理命令 ======
docker compose ps          # 查看状态
docker compose logs -f     # 查看日志（-f 持续跟随）
docker compose down        # 停止并删除容器（数据卷 pgdata/redisdata/miniodata 默认保留，不会丢数据）
docker compose down -v     # 连同数据卷一起删除（会清空数据库/Redis/MinIO 里的所有数据，谨慎使用）
```

> 现在整个"从零到能跑"的开发环境搭建已经全部完成并验证通过:后端 /health 能访问、前端页面能渲染、三个基础设施容器都是 healthy 状态。

---

```file:启动前端、后端、docker
终端 1 — 后端(在 backend 目录,conda learner 环境已激活):
  cd E:\pySpace\lingua-learner\backend
  poetry run uvicorn app.main:app --reload --port 8000
  看到 Application startup complete 就绪。

终端 2 — 前端(在 frontend 目录):
  cd E:\pySpace\lingua-learner\frontend
  pnpm run dev
  看到 Local: http://localhost:5173/ 就绪。
  
在项目根目录执行：
docker compose up -d
查看状态：
docker compose ps
停止并移除容器：
docker compose down

```


```file:软件
取名：Artifex
定位：
	Artifex 是一个全领域 AI 学习伙伴——不是老师，不是搜索引擎，也不是预言家。
	它是活在工具之中的灵：清醒、专注，随你的思维而变形。

	有别于传统 AI 交互工具追求的“即时答案交付”，Artifex 坚持不灌输、共建构的原则。
	它不替你思考，它帮你更好地思考；它不给你标准答案，它陪你亲手搭建属于自己的理解。

	你是创造者，Artifex 是你手中的器与灵。
	
功能：
1. 对话模块：从场景库中选定一个场景卡，支持文本/语音/数字人方式进行对话，结束后生成学情报告。
2. 知识库模块：支持定义领域，在该领域下定义场景卡（或导入Prompt、skill等），点击某个场景卡可以跳转到对话模块
3. 学情档案：学习记录、报告、路线、规划
4. 数字人设置（专家角色/语音音色/人物形象）
```
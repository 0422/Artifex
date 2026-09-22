# 灵犀（LinguaLearner）— 技术架构设计

**日期**：2026-08-09
**基于**：产品需求规格书 v1.0
**作者**：高级开发工程师

---

## 1. 技术栈选型

### 1.1 总览

| 层级 | 技术选型 | 选型理由 |
|------|---------|---------|
| **前端框架** | React 18 + TypeScript + Vite | 生态最丰富、PWA 支持成熟、社区活跃度最高 |
| **UI 层** | Tailwind CSS + Radix UI (无头组件) | 原子化 CSS 开发效率高；Radix 提供无障碍基座 |
| **状态管理** | Zustand + React Query (TanStack) | Zustand 轻量无模板；React Query 接管服务端状态缓存 |
| **PWA** | Workbox (vite-plugin-pwa) | 标准化 Service Worker 方案，缓存策略可配置 |
| **后端框架** | Python FastAPI | AI/ML 生态第一梯队；原生 async；自动 OpenAPI 文档 |
| **异步任务** | Celery + Redis Broker | 内容提取、卡片生成等耗时任务异步化 |
| **实时通信** | WebSocket (FastAPI 原生) | 对话练习需要低延迟双向通道 |
| **主数据库** | PostgreSQL 15 | 成熟可靠、JSONB 支持、全文搜索 |
| **向量数据库** | pgvector 扩展 | 与 PG 共存，避免多一套基础设施；语义搜索/去重 |
| **缓存** | Redis 7 | 会话、FSRS 调度队列、限流、实时状态 |
| **对象存储** | MinIO (自建) / S3 兼容 | 用户上传内容(PDF/音频/图片) |
| **LLM** | OpenAI GPT-4o / Claude 3.5 Sonnet | 内容提取、对话练习、路径生成 |
| **STT** | OpenAI Whisper API / 本地 Whisper | 多语言语音转文字 |
| **TTS** | OpenAI TTS / Edge TTS (回退) | 对话语音合成 |
| **数字人渲染** | Three.js + @pixiv/three-vrm | VRM 3D 虚拟形象渲染、表情控制、lip-sync |
| **浏览器STT** | Web Speech API (SpeechRecognition) | 零延迟零成本的客户端语音输入回退方案 |
| **Embedding** | text-embedding-3-small | 知识概念向量化，语义关联 |
| **容器化** | Docker + Docker Compose | 本地开发 & 单机部署一致性 |
| **CI/CD** | GitHub Actions | 自动化测试、构建、部署 |
| **监控** | Sentry (错误) + Grafana/Prometheus (指标) | 生产可观测性 |

### 1.2 关键选型决策

#### 为什么 FastAPI 而不是 Node.js/NestJS？

| 维度 | FastAPI (Python) | NestJS (Node.js) |
|------|-----------------|-----------------|
| AI/ML 集成 | **原生优势**：直接调用 OpenAI SDK、LangChain、Whisper、scikit-learn | 需通过 HTTP 调用 Python 微服务，增加一跳延迟 |
| FSRS 算法 | 有现成 Python 实现 (fsrs-py) | 需自行移植或调用 Python |
| 异步性能 | uvloop + asyncio，性能接近 Node.js | 事件循环天然异步 |
| 类型安全 | Pydantic v2 媲美 TypeScript | TypeScript 类型系统 |
| 团队招聘 | AI 团队通常 Python 技术栈 | 前端可复用 JS |

**结论**：AI 密集型应用选 Python，FSRS/LLM/STT/TTS/Embedding 全部原生调用，无跨语言开销。

#### 为什么 PWA 而不是 React Native/Flutter？

| 维度       | PWA                         | React Native              |
| -------- | --------------------------- | ------------------------- |
| 开发成本     | 1 套代码                       | 2 套(iOS+Android) 或 RN 桥接层 |
| 录音 API   | MediaRecorder API（需验证）      | 原生录音权限和体验更好               |
| 推送通知     | Web Push API（iOS 17.4+ 才支持） | 原生推送                      |
| 离线能力     | Service Worker 缓存           | 原生 SQLite                 |
| 8 人团队可行性 | ✅ 前端 2 人足够                  | ❌ 需额外移动端人力                |

**结论**：MVP 阶段 PWA 是最优解。PRD 已标注"M1 W3 前完成 PWA 录音 POC"，如果 MediaRecorder 在移动端表现不达标，V1.1 再考虑 Capacitor 壳方案（仍用 Web 技术栈）。

---

## 2. 系统分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    客户端层 (Client)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          PWA (React + TypeScript + Tailwind)          │  │
│  │  ┌──────────┬──────────┬──────────┬──────────────┐  │  │
│  │  │ 仪表盘   │ 内容捕获  │ AI对话   │ 学习路径     │  │  │
│  │  │ Dashboard│ Capture  │ Chat     │ LearningPath │  │  │
│  │  └──────────┴──────────┴──────────┴──────────────┘  │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │     DigitalHuman (Three.js + VRM 浮层)        │   │  │
│  │  │  Avatar渲染 │ Lip-Sync │ 表情系统 │ 悬浮模式  │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │  Service Worker  │  IndexedDB (离线兜底)             │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS + WSS
┌──────────────────────────┴──────────────────────────────────┐
│                   网关层 (Gateway)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Nginx (反向代理 + SSL 终端 + 静态资源 + 限流)        │  │
│  │  ┌────────────┬──────────────┬──────────────────┐   │  │
│  │  │ REST API   │  WebSocket   │  静态文件/CDN    │   │  │
│  │  └────────────┴──────────────┴──────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                   API / 业务服务层                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              FastAPI Application                       │  │
│  │                                                        │  │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ Auth    │ │ Capture │ │ Memory   │ │ Chat     │  │  │
│  │  │ Service │ │ Service │ │ Service  │ │ Service  │  │  │
│  │  └─────────┘ └─────────┘ └──────────┘ └──────────┘  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │Dashboard│ │ Path    │ │ Concept  │ │ Review   │  │  │
│  │  │Service  │ │ Service │ │ Graph    │ │ Service  │  │  │
│  │  └─────────┘ └─────────┘ └──────────┘ └──────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                   AI 能力层 (AI Services)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │  │
│  │  │ LLM      │ │Embedding │ │  STT     │ │  TTS   │  │  │
│  │  │ Service  │ │ Service  │ │ Service  │ │Service │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │  │
│  │  API Router + Fallback + Cost Tracker + Cache        │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                   任务队列层 (Async Workers)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Celery Workers                            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐    │  │
│  │  │ 内容提取   │ │ 卡片生成   │ │ 知识图谱更新  │    │  │
│  │  │ Worker     │ │ Worker     │ │ Worker        │    │  │
│  │  └────────────┘ └────────────┘ └────────────────┘    │  │
│  │  ┌────────────┐ ┌────────────┐                        │  │
│  │  │ 日终小结   │ │ 概念关联   │   Redis Broker       │  │
│  │  │ Worker     │ │ Worker     │                        │  │
│  │  └────────────┘ └────────────┘                        │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                    数据层 (Data Layer)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │PostgreSQL│ │ pgvector │ │  Redis   │ │  MinIO/S3    │  │
│  │ (主库)   │ │ (向量)   │ │ (缓存)   │ │ (对象存储)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块设计

### 3.1 模块总览与 P0 覆盖

```
                    ┌───────────────────────────────┐
                    │       灵犀 后端服务            │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────────┬───────────┼───────────┬───────────────┐
        │               │           │           │               │
   ┌────┴────┐   ┌──────┴─────┐ ┌──┴───┐ ┌─────┴────┐  ┌──────┴──────┐
   │  Auth   │   │  Capture   │ │Memory│ │   Chat   │  │  Dashboard  │
   │  认证   │   │  内容捕获   │ │  记忆 │ │  AI对话  │  │   仪表盘    │
   │  Module │   │  Module    │ │Module │ │  Module  │  │   Module    │
   └────┬────┘   └──────┬─────┘ └──┬───┘ └─────┬────┘  └──────┬──────┘
        │               │           │           │               │
        │  ┌────────────┴───┐       │           │     ┌─────────┴─────┐
        │  │  Concept Graph │       │           │     │  Path Module  │
        │  │   知识图谱      │       │           │     │  学习路径      │
        │  │   Module       │       │           │     └───────────────┘
        │  └────────────────┘       │           │
        │                           │    ┌──────┴──────┐
        │                           │    │ DigitalHuman │
        │                           │    │  数字人模块   │
        │                           │    │   Module     │
        │                           │    └──────┬──────┘
        │                           │           │
   ┌────┴───────────────────────────┴───────────┴────────────────────┐
   │                        AI Infrastructure                         │
   │  LLM Router │ Embedding │ STT │ TTS │ Cost Tracker │ Cache      │
   └─────────────────────────────────────────────────────────────────┘
```

### 3.2 模块详细设计

---

#### 3.2.1 Auth Module（认证模块）

**职责**：用户注册/登录、JWT 签发与刷新、OAuth 集成（可选）

**技术细节**：
- JWT access token (15min) + refresh token (7d, httpOnly cookie)
- bcrypt 密码哈希
- 可选：Google/Apple OAuth（P1）

**数据模型**：
```
User (id, email, password_hash, nickname, avatar_url, created_at, updated_at)
UserProfile (user_id, native_language, timezone, daily_goal_minutes, onboarding_completed)
```

---

#### 3.2.2 Capture Module（资料组织与概念提取）→ 覆盖 P0-1

**职责**：接收用户输入内容（学习资料，主体在软件外）→ 异步提取概念 → 建立知识关联 → 触发记忆卡片生成 → 归位到路径对应环节

**子模块**：

| 子模块 | 职责 | 关键技术 |
|--------|------|---------|
| **Input Handler** | 接收粘贴文本/URL/PDF上传（可带 `path_milestone_id`） | BeautifulSoup(URL抓取)、PyPDF2(PDF解析) |
| **Concept Extractor** | 调用 LLM 提取关键概念(≥3个) + 摘要 | GPT-4o prompt engineering |
| **Relation Mapper** | 标注与已有知识图谱的关联 | pgvector 语义相似度搜索 |
| **Resource Router** | 无 `path_milestone_id` 时由 LLM 判定资料归位到路径的哪一环节（跨模块协作） | LLM 对照里程碑主题判定 |
| **Card Trigger** | 触发 Memory Module 生成卡片 | Celery 异步任务链 |

**API**：
```
POST   /api/v1/capture          # 提交内容（文本/URL/文件）
GET    /api/v1/capture/{id}     # 查询处理状态
GET    /api/v1/capture/{id}/concepts  # 获取提取的概念列表
```

**处理流水线**（Celery Chain）：
```
content_received → extract_clean_text → llm_extract_concepts → 
  vector_search_relations → save_concepts → trigger_card_generation
```

**验收标准映射**：
- 粘贴内容 30s 内返回 ≥3 个概念 + 摘要：通过 WebSocket 推送进度，首屏概念 5s 内展示，完整结果 ≤30s
- 标注已有知识关联：pgvector top-k 语义搜索，阈值 cosine_similarity > 0.75 视为关联

---

#### 3.2.3 Memory Module（智能记忆系统）→ 覆盖 P0-2

**职责**：FSRS 调度引擎 + 卡片生命周期管理 + 跨领域去重合并

**子模块**：

| 子模块 | 职责 | 关键技术 |
|--------|------|---------|
| **Card Generator** | 按领域模板生成卡片（词汇/概念/技法） | LLM + 领域专用 prompt |
| **FSRS Scheduler** | 核心间隔重复调度算法 | fsrs-py 库 (Rust 绑定) |
| **Dedup Engine** | 跨领域检测重复/相似卡片并合并 | pgvector 向量相似度 + 规则 |
| **Review Handler** | 处理用户复习结果，更新卡片状态 | FSRS 评分 → 更新间隔 |
| **Daily Queue Builder** | 每日凌晨生成当日复习队列 | Celery 定时任务，Redis 缓存 |

**FSRS 参数**（来自 PRD 用户研究）：
```python
# 外语: retention=0.90
# 人文: retention=0.85  
# 兴趣陈述性知识: retention=0.90
# 兴趣程序性知识: 距上次练习天数
```

**卡片模型**：
```
Card (
  id, user_id, domain, card_type,  # domain: language/humanities/skill
  front_content, back_content,      # 正面/背面内容
  source_concept_id,                # 来源概念
  fsrs_state,                       # FSRS 状态 (JSONB)
  due_at, stability, difficulty,
  review_count, lapses,
  is_merged, merged_from_ids,
  created_at, updated_at
)
```

**每日队列生成逻辑**：
```python
# 伪代码
def build_daily_queue(user_id: str, target_minutes: int) -> list[Card]:
    cards = get_due_cards(user_id)          # WHERE due_at <= NOW()
    cards = sort_by_priority(cards)          # overdue > critical > normal
    cards = interleave_domains(cards)        # 外语/人文/兴趣交替
    cards = cap_by_time(cards, target_minutes * 0.8)  # 留 20% 缓冲
    return cards
```

---

#### 3.2.4 Chat Module（检验对话·费曼式）→ 覆盖 P0-3

**职责**：全领域检验对话——外语场景对话 + 人文费曼解释 + 兴趣练习汇报，通过谈论检验掌握程度，检验结果驱动路径更新

**子模块**：

| 子模块 | 职责 | 关键技术 |
|--------|------|---------|
| **Session Manager** | 管理对话生命周期、场景上下文 | WebSocket + Redis 会话状态 |
| **Scenario Engine** | 加载检验模式：外语场景（日常/商务/旅行）/ 人文费曼（概念解释追问）/ 兴趣汇报（练习回顾） | 模式模板 + System Prompt |
| **Correction Engine** | 渐进式纠错：说对确认，小错轻轻纠正，大错引导重述 | LLM 纠错 prompt 链 |
| **Assessment Engine** | 判定掌握程度（外语 CEFR 估计 / 人文概念一致性对照图谱 / 技能熟练度），输出薄弱点 | LLM 判定 + 知识图谱比对 |
| **Report Generator** | 对话结束生成检验报告(≥3薄弱点+≥3卡片)，写入 LearningEvent 驱动路径更新 | LLM 摘要 + 卡片自动入库 |

**WebSocket 协议**：
```json
// Client → Server
{
  "type": "start_session",
  "mode": "feynman",              // scenario:外语场景 / feynman:人文费曼 / checkin:兴趣汇报
  "scenario": "restaurant_order", // scenario 模式使用
  "language": "ja",
  "difficulty": "N4"
}
{
  "type": "audio_chunk",
  "data": "<base64>"
}
{
  "type": "text_message",
  "content": "すみません、メニューをください"
}
{
  "type": "end_session"
}

// Server → Client
{
  "type": "ai_response",
  "text": "はい、こちらがメニューでございます。",
  "audio_url": "/api/v1/tts/stream/xxx",
  "correction": null
}
{
  "type": "correction",
  "original": "メニューをください",
  "corrected": "メニューを見せてください",
  "severity": "minor",
  "explanation": "「をください」でも通じますが、より自然な表現です"
}
{
  "type": "session_report",
  "duration_seconds": 185,
  "assessment": { "dimension": "concept_consistency", "score": "A", "weak_points": [] },
  "stuck_points": [...],
  "generated_cards": [...],
  "cefr_estimate": "A2.2"
}
```

**回退策略**（来自 PRD 风险提示）：
- MVP 接受"文本优先"：语音输入转文字后走文本对话，TTS 合成语音输出
- 如果 PWA 录音体验不达标，首版仅支持文本对话
- 首版仅英日双语 + 3 个高频场景；人文费曼先做"单轮解释→判定"简化版，多轮追问（P1-1）留 V1.1

---

#### 3.2.5 Dashboard Module（仪表盘）→ 覆盖 P0-4

**职责**：跨领域进度可视化 + DLE 趋势 + MHI 状态灯 + 日终小结

**子模块**：

| 子模块 | 职责 |
|--------|------|
| **Progress Rings** | 各领域进度环渲染数据 |
| **DLE Calculator** | 日均学习效能计算（有意义事件 × 深度 / 总时间） |
| **MHI Monitor** | 动力健康度评估 + 状态灯 |
| **Daily Digest** | 日终小结生成（Celery 定时 21:00） |

**DLE 计算**（来自 PRD）：
```python
DLE = sum(event.significance * event.depth for event in today_events) / total_learning_minutes
# significance: card_review=1, concept_discovery=2, conversation_practice=3, output_challenge=5
# depth: shallow=0.5, moderate=1.0, deep=2.0
```

**MHI 状态机**：
```python
MHI = 0.30 * consistency_score + 0.25 * engagement_score + 0.25 * progress_perception + 0.20 * mood_score
# 🟢 > 0.7  → 健康
# 🟡 0.5-0.7 → 注意（3 天空白）
# 🟠 0.3-0.5 → 警告（7 天 5 天空白）
# 🔴 < 0.3  → 危险（14 天空白）
```

---

#### 3.2.6 Path Module（领域路径引擎）→ 覆盖 P0-5

**职责**：领域添加 → 问卷（起点+目标分析）→ 路径生成 → 资料推荐与自动归位 → 检验驱动实时更新

**子模块**：

| 子模块 | 职责 |
|--------|------|
| **Onboarding Engine** | 添加领域时发起轻量问卷：对这个领域的了解程度 / 想学习掌握什么（复用新用户引导交互） |
| **Starting Point Analyzer** | LLM 分析问卷 → 生成起点报告（level_summary / strengths / gaps / recommendation） |
| **Path Generator** | 基于起点 + 目标 + 领域模板 → 生成初始学习路径（有序里程碑序列，第一个 CURRENT 其余 LOCKED） |
| **Resource Router** | 推荐学习资料 + 用户手动添加资料 → LLM 自动归位到路径对应环节（资料主体在软件外，Capture 记录挂 `path_milestone_id`） |
| **Assessment Engine** | 消费检验对话结果（LearningEvent）→ 判定里程碑推进 / 薄弱点重排 |
| **Adaptive Adjuster** | 依据检验结果实时更新路径：推进里程碑、调整后续环节、重新生成"今日任务" |

---

#### 3.2.7 Concept Graph Module（知识图谱）

**职责**：管理跨领域概念节点和关联边，支撑"跨领域概念联结"(P1-3)

**数据模型**：
```
ConceptNode (id, user_id, domain, label, definition, embedding, created_at)
ConceptEdge (id, source_id, target_id, relation_type, weight, is_ai_generated)
```

**关系类型**：
- `prerequisite`：A 是 B 的前置知识
- `analogy`：跨领域类比（如"音乐的和弦进行 ≈ 语言的语法结构"）
- `contrast`：概念对比
- `extends`：A 是 B 的深化

---

#### 3.2.8 DigitalHuman Module（桌面数字人）→ 覆盖 P1-6

**职责**：VRM 虚拟形象渲染 + 语音驱动双向交互 + 上下文表情系统 + 悬浮陪伴模式

**子模块**：

| 子模块 | 职责 | 关键技术 |
|--------|------|---------|
| **Avatar Renderer** | 加载/渲染 VRM 模型，闲置动画循环（眨眼/呼吸/微动作） | Three.js + @pixiv/three-vrm |
| **Lip-Sync Engine** | 分析 TTS 音频流实时驱动下颌/口型骨骼 | Web Audio API → 振幅采样 → VRM BlendShape |
| **Expression Engine** | 根据对话语义/学习状态切换面部表情 | VRM ExpressionManager (happy/angry/sad/relaxed/surprised) |
| **Voice Interaction** | 语音输入(STT) + 语音输出(TTS) 的全链路管理 | Web Speech API + Edge TTS / OpenAI TTS |
| **Float Widget** | 悬浮小组件模式（120×120px），其他任务中持续在线 | CSS `position: fixed` + Canvas 降采样渲染 |
| **Session Bridge** | 与 Chat Module 共享对话上下文，数字人作为可视化前端 | 共享 WebSocket 会话 + Redis 状态 |

**架构关系**：

```
┌─────────────────────────────────────────────────────┐
│              DigitalHuman Module (前端)               │
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Avatar     │  │  Lip-Sync    │  │ Expression │ │
│  │  Renderer    │  │   Engine     │  │   Engine   │ │
│  │ (Three.js)   │  │ (Web Audio)  │  │  (VRM BS)  │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                 │                 │        │
│  ┌──────┴─────────────────┴─────────────────┴──────┐ │
│  │              Voice Interaction                   │ │
│  │  [STT] ← Web Speech API / Whisper               │ │
│  │  [TTS] → Edge TTS / OpenAI TTS → Audio Stream   │ │
│  └──────────────────────┬──────────────────────────┘ │
│                         │                             │
│  ┌──────────────────────┴──────────────────────────┐ │
│  │           Session Bridge (共享 Chat WS)          │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
          │ 共享 WebSocket
          ▼
┌─────────────────────┐
│   Chat Module (后端)  │  ← 复用现有对话/纠错/报告能力
└─────────────────────┘
```

**Lip-Sync 实现方案**（音频振幅驱动）：
```python
# 伪代码 — 前端 TypeScript 实现
class LipSyncEngine {
  // 从 TTS 音频流中实时采样振幅，驱动 VRM 口型 BlendShape
  processAudio(audioBuffer: AudioBuffer) {
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    // 每帧采样音量 RMS → 映射到 VRM Jaw BlendShape 权重 (0-1)
    const rms = calculateRMS(analyser)
    vrm.expressionManager.setValue('aa', rms * 1.2)  // 张嘴
    vrm.expressionManager.update()
  }
}
```

**表情触发规则**：

| 触发条件 | 表情 | VRM BlendShape | 持续时间 |
|---------|------|---------------|---------|
| 对话开始 | 微笑 | happy (0.6) | 2s → idle |
| 用户回答正确 | 开心 | happy (1.0) | 1.5s |
| 用户出错/卡顿 | 温和 | relaxed (0.5) | 1s |
| AI 思考中 | 专注 | (眨眼+微点头) | 持续至回复 |
| 鼓励/赞美 | 庆祝 | happy (0.8) + Surprised (0.3) | 2s |
| 对话结束 | 告别 | happy (0.6) + 挥手 | 3s |
| MHI 🔴 危险 | 关切 | sad (0.5) | 持续 |

**API**：
```
POST   /api/v1/digital-human/config          # 更新数字人配置（模型/音色/语言）
GET    /api/v1/digital-human/models           # 获取可用 VRM 模型列表
WS     /ws/v1/digital-human                   # 数字人专用 WebSocket（语音流 + 表情指令）
```

**WebSocket 协议扩展**（复用 Chat WS + 新增消息类型）：
```json
// Server → Client（数字人控制指令）
{
  "type": "avatar_expression",
  "expression": "happy",
  "intensity": 0.8,
  "duration_ms": 1500
}
{
  "type": "avatar_speak",
  "text": "いらっしゃいませ！何名様ですか？",
  "audio_url": "/api/v1/tts/stream/xxx",
  "viseme_timeline": null   // 若 TTS 支持 viseme 则填充
}
{
  "type": "avatar_idle_gesture",
  "gesture": "wave"   // 挥手/点头/摇头等手势动画
}

// Client → Server（语音输入）
{
  "type": "voice_input_start",
  "stt_engine": "web_speech"  // 或 "whisper_api"
}
{
  "type": "audio_chunk",
  "data": "<base64>"
}
{
  "type": "voice_input_end"
}
```

**悬浮模式实现**：
- 桌面端：CSS `position: fixed; bottom: 24px; right: 24px` + 120×120 Canvas
- 渲染降级：悬浮模式下降低 VRM 骨骼更新频率至 15fps，减少 GPU 占用
- 交互保留：点击悬浮窗展开为完整对话面板，再次点击收起
- 语音保持：悬浮模式下仍监听唤醒词，用户可随时语音唤起对话

**数据模型**：
```
DigitalHumanConfig (
  id, user_id,
  vrm_model_url,                # VRM 模型资源地址
  voice_provider,               # TTS 提供商 (edge_tts / openai_tts)
  voice_id,                     # 音色 ID
  stt_engine,                   # STT 引擎 (web_speech / whisper_api / whisper_local)
  wake_word_enabled,            # 是否启用唤醒词
  wake_word,                    # 唤醒词文本
  float_widget_enabled,         # 是否启用悬浮模式
  expression_intensity,         # 表情强度 (0-1)
  idle_animation_enabled,       # 闲置动画开关
  created_at, updated_at
)
```

**回退策略**：
- 浏览器不支持 WebGL 2.0 → 降级为 CSS/SVG 简化形象 + 纯文本对话
- Web Speech API 不可用（如 Firefox 部分版本）→ 降级为 Whisper API + 手动点击录音
- VRM 模型加载失败 → 显示默认头像 + 继续语音对话功能
- 移动端性能不足 → 不渲染 3D 形象，仅保留语音交互 + 静态头像

---

## 4. 数据模型 ER 概要

```
User ──1:N──> UserProfile
User ──1:1──> DigitalHumanConfig
User ──1:N──> Capture
User ──1:N──> Card
User ──1:N──> ConceptNode
User ──1:N──> ChatSession
User ──1:N──> LearningEvent
User ──1:N──> LearningPath

Capture ──1:N──> ConceptNode
ConceptNode ──1:N──> Card
ConceptNode ──1:N──> ConceptEdge(source/target)

ChatSession ──1:N──> ChatMessage
ChatSession ──1:N──> Card (练习报告生成的卡片)

Card ──1:N──> ReviewLog

LearningPath ──1:N──> PathMilestone
PathMilestone ──1:N──> Capture (资料归位: path_milestone_id)
ChatSession ──1:N──> LearningEvent (检验结果回流路径)
```

---

## 5. 目录结构

```
lingua-learner/
├── frontend/                      # React PWA
│   ├── src/
│   │   ├── components/           # 通用组件
│   │   │   ├── ui/               # Radix UI 封装
│   │   │   ├── dashboard/        # 仪表盘组件
│   │   │   ├── capture/          # 内容捕获组件
│   │   │   ├── chat/             # AI 对话组件
│   │   │   ├── digital-human/    # 桌面数字人组件
│   │   │   │   ├── AvatarRenderer.tsx    # VRM 渲染器
│   │   │   │   ├── LipSyncEngine.ts      # 口型同步引擎
│   │   │   │   ├── ExpressionEngine.ts   # 表情系统
│   │   │   │   ├── VoiceInteraction.tsx  # 语音交互面板
│   │   │   │   ├── FloatWidget.tsx       # 悬浮小组件
│   │   │   │   └── DigitalHumanPanel.tsx # 数字人主面板
│   │   │   └── memory/           # 复习卡片组件
│   │   ├── hooks/                # 自定义 hooks
│   │   ├── stores/               # Zustand stores
│   │   ├── services/             # API 调用层
│   │   ├── lib/                  # 工具函数
│   │   └── pages/                # 路由页面
│   ├── public/
│   └── vite.config.ts
│
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── capture.py
│   │   │   │   ├── memory.py
│   │   │   │   ├── chat.py       # REST + WebSocket
│   │   │   │   ├── digital_human.py  # 数字人 REST + WS
│   │   │   │   ├── dashboard.py
│   │   │   │   └── path.py
│   │   │   └── deps.py           # 依赖注入
│   │   ├── core/
│   │   │   ├── config.py         # 配置管理
│   │   │   ├── security.py       # JWT/权限
│   │   │   └── database.py       # DB 连接池
│   │   ├── models/               # SQLAlchemy ORM
│   │   │   ├── user.py
│   │   │   ├── capture.py
│   │   │   ├── card.py
│   │   │   ├── concept.py
│   │   │   ├── chat.py
│   │   │   ├── digital_human.py
│   │   │   └── event.py
│   │   ├── schemas/              # Pydantic 验证
│   │   ├── services/             # 业务逻辑
│   │   │   ├── capture_service.py
│   │   │   ├── memory_service.py
│   │   │   ├── fsrs_engine.py
│   │   │   ├── chat_service.py
│   │   │   ├── digital_human_service.py
│   │   │   ├── dashboard_service.py
│   │   │   ├── path_service.py
│   │   │   └── concept_graph_service.py
│   │   ├── ai/                   # AI 能力封装
│   │   │   ├── llm.py            # LLM Router (OpenAI/Claude)
│   │   │   ├── embedding.py      # Embedding 服务
│   │   │   ├── stt.py            # 语音识别
│   │   │   ├── tts.py            # 语音合成
│   │   │   └── cost_tracker.py   # Token 用量追踪
│   │   └── workers/              # Celery 任务
│   │       ├── extract_concepts.py
│   │       ├── generate_cards.py
│   │       ├── build_queue.py
│   │       ├── daily_digest.py
│   │       └── update_graph.py
│   ├── alembic/                  # DB 迁移
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml            # 本地开发环境
├── docker-compose.prod.yml       # 生产部署
└── README.md
```

---

## 6. API 设计（P0 核心接口）

### 6.1 REST API 总览

| 方法 | 路径 | 模块 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | Auth | 注册 |
| POST | `/api/v1/auth/login` | Auth | 登录 |
| POST | `/api/v1/auth/refresh` | Auth | 刷新 Token |
| POST | `/api/v1/capture` | Capture | 提交内容（可带 `path_milestone_id` 归位到路径环节） |
| GET | `/api/v1/capture/{id}` | Capture | 查询处理状态 |
| GET | `/api/v1/capture/{id}/concepts` | Capture | 获取提取概念 |
| GET | `/api/v1/memory/due` | Memory | 今日待复习队列 |
| POST | `/api/v1/memory/review` | Memory | 提交复习结果 |
| GET | `/api/v1/memory/cards` | Memory | 卡片列表(分页) |
| GET | `/api/v1/memory/stats` | Memory | FSRS 统计 |
| WS | `/ws/v1/chat` | Chat | 检验对话 WebSocket |
| GET | `/api/v1/chat/sessions` | Chat | 历史对话列表 |
| GET | `/api/v1/chat/sessions/{id}` | Chat | 对话详情+报告 |
| GET | `/api/v1/dashboard/overview` | Dashboard | 仪表盘总览 |
| GET | `/api/v1/dashboard/dle-trend` | Dashboard | DLE 趋势(7/30d) |
| GET | `/api/v1/dashboard/mhi` | Dashboard | MHI 状态+历史 |
| GET | `/api/v1/path/current` | Path | 当前学习路径 |
| GET | `/api/v1/path/onboarding` | Path | 引导流程步骤 |
| POST | `/api/v1/path/onboarding/complete` | Path | 完成引导，生成起点报告 |
| POST | `/api/v1/path/domains` | Path | 添加学习领域，触发问卷+路径生成 |
| GET | `/api/v1/path/domains/{id}/today` | Path | 今日学习任务（当前里程碑推进项） |
| GET | `/api/v1/concepts` | Concept | 概念列表 |
| GET | `/api/v1/concepts/{id}/graph` | Concept | 概念邻域图谱 |
| GET | `/api/v1/digital-human/config` | DigitalHuman | 获取数字人配置 |
| PUT | `/api/v1/digital-human/config` | DigitalHuman | 更新数字人配置 |
| GET | `/api/v1/digital-human/models` | DigitalHuman | 可用 VRM 模型列表 |
| WS | `/ws/v1/digital-human` | DigitalHuman | 数字人语音流+表情指令 |

### 6.2 WebSocket 协议（对话）

连接：`ws://host/ws/v1/chat?token=<jwt>`

消息类型见 3.2.4 Chat Module。

---

## 7. AI 成本控制策略

这是 PRD 标红的阻塞风险之一。分层策略：

| 策略 | 说明 | 预估节省 |
|------|------|:------:|
| **LLM 分级路由** | 简单任务(GPT-3.5/Claude Haiku) vs 复杂任务(GPT-4o/Claude Sonnet) | 40-60% |
| **Embedding 缓存** | 已提取概念的 embedding 缓存，避免重复计算 | 20-30% |
| **对话上下文窗口控制** | 滑动窗口 4K tokens，旧消息摘要压缩 | 30-50% |
| **TTS 预合成缓存** | 高频对话场景的 TTS 音频预生成并缓存 | 50-70% |
| **本地 STT 模型** | 使用本地 Whisper 而非 API（M1 Spike A 评估） | 80-100% STT 成本 |
| **每日 Token 预算** | 单用户日 Token 上限（如 GPT-4o 10K/day） | 硬上限 |
| **数字人 STT 浏览器优先** | 数字人语音输入优先用 Web Speech API（零成本），Whisper API 仅作回退 | 80-100% STT 成本 |
| **数字人 TTS 使用 Edge TTS** | 数字人语音输出默认用 Edge TTS（免费），OpenAI TTS 仅在高音质场景 | 90-100% TTS 成本 |
| **VRM 模型 CDN 缓存** | VRM 模型文件通过 CDN 长缓存，避免重复下载（单模型 2-10MB） | 带宽成本 |

单用户日成本估算（需 M1 W2 验证）：
```
内容提取: 1-3 次/天 × 2K tokens × $0.01/1K  = $0.02-0.06
对话练习: 1-2 次/天 × 4K tokens × $0.01/1K  = $0.04-0.08
卡片生成: 3-10 张/天 × 500 tokens × $0.01/1K = $0.015-0.05
Embedding: 10-30 次/天 × $0.00002/1K          = $0.001
日终小结: 1 次/天 × 2K tokens                  = $0.02
────────────────────────────────────────────────
预估日成本: $0.10-0.25 / 用户
月成本: $3-7.5 / 用户
```

---

## 8. 部署架构

```
                         ┌──────────────┐
                         │   Cloudflare │
                         │  DNS + CDN   │
                         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │       Nginx            │
                    │  (反向代理 + SSL)       │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
     ┌────────┴────────┐ ┌─────┴──────┐ ┌────────┴────────┐
     │  FastAPI x2     │ │  Celery    │ │  Static Files   │
     │  (uvicorn)      │ │  Workers   │ │  (PWA build)    │
     │  :8000          │ │  x4        │ │                 │
     └────────┬────────┘ └─────┬──────┘ └─────────────────┘
              │                │
     ┌────────┴────────────────┴────────┐
     │                                   │
┌────┴─────┐ ┌──────┴──────┐ ┌─────────┴──┐
│PostgreSQL│ │   Redis     │ │  MinIO/S3  │
│ +pgvector│ │:6379        │ │ :9000      │
└──────────┘ └─────────────┘ └────────────┘
```

**MVP 阶段**：单机 Docker Compose 部署（1 台 4C8G VPS 可承载 50-100 种子用户）

**扩展路径**：
- DB 读写分离 → PostgreSQL 主从
- API 水平扩展 → FastAPI × N + Load Balancer
- Celery Worker 独立扩缩
- Redis Sentinel / Cluster

---

## 9. 关键技术风险与缓解

| 风险 | 等级 | 缓解措施 | 决策节点 |
|------|:--:|---------|:------:|
| PWA 录音体验不达标 | 🔴 | M1 W3 完成 PWA 录音 POC；回退方案：文本优先 | W3 |
| AI 对话延迟 > 2s | 🔴 | 流式响应 + 预加载场景上下文 + TTS 流式输出 | W7-8 |
| AI 单用户月成本 > $15 | 🟡 | 分级路由 + 缓存 + 本地模型 | W2 (成本模型) |
| FSRS 算法实现偏差 | 🟡 | 使用社区验证的 fsrs-py 库，对比 Anki FSRS 基准 | W2-3 (Spike B) |
| 日语 STT 准确率 | 🟡 | OpenAI Whisper 日语测试 + 备选 Azure Speech | W1-2 (Spike A) |
| 数字人 VRM 渲染性能 | 🟡 | 桌面端 60fps 验证 + 悬浮模式降级至 15fps + 移动端不渲染 3D | V1.1 W17-18 |
| 数字人 Lip-Sync 效果 | 🟡 | 音频振幅驱动方案先验证；若效果差再评估 Viseme 方案 | V1.1 W17 |
| Web Speech API 浏览器兼容 | 🟡 | Chrome/Edge 优先支持；Firefox 回退 Whisper API；Safari 需测试 | V1.1 W17 |

---

## 10. M1 技术预研清单（W1-3 必须完成）

| Spike | 内容 | 负责人 | 产出 |
|-------|------|--------|------|
| **A** | STT/TTS 选型：非母语准确率 + 延迟 + 成本 | AI 工程师 | 选型报告 + POC 代码 |
| **B** | FSRS 引擎评估：fsrs-py 集成 + 与 Anki 基准对比 | 后端 | 集成测试 + 基准数据 |
| **C** | PWA 录音 POC：MediaRecorder + 移动端浏览器兼容 | 前端 | Demo + 兼容矩阵 |
| **D** | 数字人 VRM 渲染 POC：three-vrm 加载 + Lip-Sync + 表情切换 + 60fps 验证 | 前端 | Demo + 性能基准（V1.1 W17 前完成） |

---

> 本文档对应 PRD 阶段：技术预研前。待 M1 三个 Spike 完成后需回补选型结论。FSRS 参数调优、对话 prompt 工程、成本模型细节留待详细设计阶段展开。P1-6 桌面数字人模块的 Spike D 预研需在 V1.1 启动前（W16-17）完成。

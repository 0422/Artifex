# 📚 灵犀（LinguaLearner）文档

> **全领域AI学习伙伴** — 从内容捕获到智能复习，一个Agent管三个世界。

---

## 🚀 快速开始

适合首次接触项目的开发者，从这里开始：

| 文档 | 说明 | 预计阅读时间 |
|------|------|------------|
| [快速开始](getting-started/quick-start.md) | 项目初始化指南，5分钟跑起来 | 5 min |
| [开发环境搭建](getting-started/development-setup.md) | 详细的 Conda + Poetry + Node 环境配置 | 15 min |
| [产品需求规格书](design/prd.md) | PRD文档，了解"为什么做" | 20 min |

---

## 🏗️ 架构设计

深入理解系统设计和技术选型：

| 文档 | 说明 | 目标读者 |
|------|------|---------|
| [架构总览](architecture/overview.md) | 🚧 待补充 — 系统整体架构图 | 所有开发者 |
| [后端架构](architecture/backend.md) | 🚧 待补充 — FastAPI + SQLAlchemy 架构 | 后端开发者 |
| [前端架构](architecture/frontend.md) | 🚧 待补充 — React + TypeScript 架构 | 前端开发者 |
| [数据库设计](architecture/database.md) | 🚧 待补充 — ER图 + 表结构说明 | 全栈开发者 |
| [Nanobot集成](architecture/nanobot-integration.md) | Nanobot集成架构设计 | AI工程师 |

---

## 🎨 设计文档

产品设计、UI规范和研究文档：

| 文档 | 说明 | 版本 |
|------|------|------|
| [PRD](design/prd.md) | 产品需求规格书 | v1.0 (2026-08-09) |
| [UI设计规范](design/ui-design.md) | 界面设计规范和组件库 | v1.0 |
| [技术架构设计](design/technical-design.md) | 技术选型、模块划分、API设计 | v1.0 |
| [用户调研](design/research.md) | 目标用户画像和设计洞察 | v1.0 |

### 开发阶段文档

记录每个开发阶段的实施过程和决策：

| 阶段 | 文档 | 核心内容 | 完成时间 |
|------|------|---------|---------|
| M1 | [框架搭建](design/phases/M1.md) | 数据模型、Auth模块、前后端脚手架 | 2026-08-15 |
| M2 | [场景对话闭环](design/phases/M2.md) | 对话流、消息持久化、引导策略 | 2026-08-15 |
| M3 | [流式语音与数字人](design/phases/M3.md) | 语音对话、数字人形象、流式响应 | 2026-08-15 |
| M4 | [知识库](design/phases/M4.md) | 知识图谱、向量检索、pgvector | 2026-08-16 |
| M5 | [工具库](design/phases/M5.md) | 工具调用系统、MCP集成 | 2026-08-17 |
| M6 | [世势洞察](design/phases/M6.md) | 🚧 规划中 | - |

---

## 📖 使用指南

### 功能说明

| 功能 | 文档 | 状态 |
|------|------|------|
| 内容捕获 | [capture.md](guides/features/capture.md) | 🚧 待补充 |
| 智能复习 | [review.md](guides/features/review.md) | 🚧 待补充 |
| AI对话 | [chat.md](guides/features/chat.md) | 🚧 待补充 |
| 知识图谱 | [knowledge-base.md](guides/features/knowledge-base.md) | 🚧 待补充 |

### 用户手册

- [用户指南](guides/user-guide.md) — 🚧 待补充

---

## 🔌 API文档

- [API参考](api/api-reference.md) — 🚧 待补充（FastAPI Swagger: http://localhost:8000/docs）

---

## 🛠️ 开发相关

| 文档 | 说明 |
|------|------|
| [贡献指南](development/contributing.md) | 🚧 待补充 |
| [更新日志](development/changelog.md) | 🚧 待补充 |
| [常见问题](development/troubleshooting.md) | 🚧 待补充 |

---

## 🎯 快速导航

### 我是新用户
1. 阅读 [产品需求规格书](design/prd.md) 了解产品愿景
2. 查看 [快速开始](getting-started/quick-start.md) 运行项目
3. 阅读 [用户指南](guides/user-guide.md) 学习使用

### 我是后端开发者
1. 阅读 [开发环境搭建](getting-started/development-setup.md) 配置环境
2. 阅读 [技术架构设计](design/technical-design.md) 了解架构
3. 阅读 [后端架构](architecture/backend.md) 🚧
4. 参考 [M1-M6阶段文档](design/phases/) 了解开发历程

### 我是前端开发者
1. 阅读 [快速开始](getting-started/quick-start.md) 运行项目
2. 阅读 [UI设计规范](design/ui-design.md) 了解设计系统
3. 阅读 [前端架构](architecture/frontend.md) 🚧

### 我是AI工程师
1. 阅读 [Nanobot集成](architecture/nanobot-integration.md) 了解AI架构
2. 参考 [M3-M4阶段文档](design/phases/) 了解AI相关实现

---

## 📂 目录结构说明

```
docs/
├── README.md                    # 📚 文档索引（本文件）
├── getting-started/             # 🚀 快速开始
│   ├── quick-start.md          # 项目初始化指南
│   └── development-setup.md    # 开发环境搭建
├── architecture/               # 🏗️ 架构设计
│   ├── nanobot-integration.md  # Nanobot集成架构
│   └── ...                     # 🚧 待补充
├── guides/                     # 📖 使用指南
│   ├── user-guide.md           # 用户手册
│   └── features/               # 功能说明
│       └── ...                 # 🚧 待补充
├── api/                        # 🔌 API文档
│   └── api-reference.md        # 🚧 待补充
├── development/                # 🛠️ 开发相关
│   └── ...                     # 🚧 待补充
└── design/                     # 🎨 设计文档
    ├── prd.md                  # 产品需求规格书
    ├── technical-design.md     # 技术架构设计
    ├── ui-design.md            # UI设计规范
    ├── research.md             # 用户调研
    └── phases/                 # 开发阶段文档
        ├── M1.md               # 框架搭建
        ├── M2.md               # 场景对话闭环
        ├── M3.md               # 流式语音与数字人
        ├── M4.md               # 知识库
        ├── M5.md               # 工具库
        └── M6.md               # 世势洞察
```

---

## 🗺️ 文档规范

本文档遵循以下开源项目文档标准：

- **FastAPI** — https://fastapi.tiangolo.com/
- **React** — https://react.dev/
- **Vue.js** — https://vuejs.org/guide/introduction.html
- **GitHub Docs** — https://docs.github.com/

### 贡献文档

欢迎补充和完善文档！请参考 [贡献指南](development/contributing.md) 🚧。

---

**项目信息**

- **项目名称**: 灵犀（LinguaLearner）
- **创建时间**: 2026-08-13
- **文档版本**: v1.0
- **最后更新**: 2026-09-22

> 💡 **提示**: 🚧 标记的文档正在规划中，欢迎参与贡献！

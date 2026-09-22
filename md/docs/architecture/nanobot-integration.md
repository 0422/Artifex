# Artifex — Nanobot 集成架构设计

**日期**：2026-08-14
**基于**：产品需求规格书 v1.0 / 技术架构设计 v1.1
**作者**：高级开发工程师
**状态**：方案评审中

---

## 0. 文档目的

本文档系统化分析 Artifex 项目中所有 LLM 交互点，评估哪些适合通过 nanobot（HKUDS 超轻量 AI Agent 框架）处理，哪些应保留在现有 FastAPI 架构中，并给出最终集成方案与实现细节。

**核心结论**：不引入 nanobot 作为独立服务，而是在 FastAPI 内部自建轻量 Agent Loop 模块，复用现有 LLM Router 和数据基础设施。nanobot 的源码（~4000 行）作为 Agent Loop 设计参考。

---

## 1. Nanobot 概述

### 1.1 项目概况

| 属性 | 说明 |
|------|------|
| 全称 | HKUDS nanobot |
| 仓库 | github.com/HKUDS/nanobot |
| 语言 | Python |
| 代码量 | ~4000 行 |
| 定位 | 超轻量个人 AI Agent 框架 |
| 许可证 | MIT |

### 1.2 核心能力

| 能力 | 说明 | Artifex 是否已有等价物 |
|------|------|:--:|
| **Agent Loop** | LLM 自主多步推理 + 工具调用循环 | ❌ 无（需新增） |
| **Skills 系统** | Python 函数注册为可被 LLM 调用的工具 | ❌ 无（需新增） |
| **Cron 定时触发** | 内置 Cron 调度器，定时触发 Agent 任务 | ✅ Celery Beat |
| **Memory 持久化** | 对话上下文 + 长期记忆存储 | ✅ PostgreSQL + Redis |
| **Provider 抽象** | 多 LLM 路由（OpenRouter / Groq / Gemini / 本地） | ✅ `ai/llm.py` LLM Router |
| **Channels** | Telegram / WhatsApp 等 IM 渠道集成 | ❌ 无（但不需要） |
| **Subagent** | 子 Agent 委派执行 | ❌ 无（需新增） |
| **Docker 部署** | 容器化一键启动 | ✅ 已有 Docker Compose |

### 1.3 Agent Loop 工作原理

nanobot 的核心是 Agent Loop——LLM 在推理过程中可以自主决定调用哪些工具、何时停止：

```
用户输入 → System Prompt + Context 注入
           ↓
    ┌──→ LLM 推理
    │      ↓
    │   是否需要调用工具？
    │      ├─ 是 → 调用 Skill → 获取结果 → 注入上下文 ──┘
    │      └─ 否 → 返回最终回复
    │
    └── 循环（最多 N 次迭代）
```

与传统的"单次 Prompt → 单次输出"模式相比，Agent Loop 适用于：
- LLM 需要在多步推理中**自主决定**调用哪些工具
- 任务流程**无法预先硬编码**为固定 if/else 分支
- 需要 LLM 综合多个数据源的信息后做出决策

---

## 2. Artifex LLM 交互点全景清单

### 2.1 交互点枚举

基于产品需求规格书和技术架构设计，Artifex 共有 **13 个 LLM 交互点**：

| # | 交互点 | 所属需求 | 所属模块 | LLM 交互模式 | 延迟要求 |
|---|--------|---------|---------|-------------|---------|
| 1 | 概念提取 | P0-1 | Capture | 单次 Prompt → 结构化 JSON | ≤30s（异步） |
| 2 | 卡片生成 | P0-2 | Memory | 单次 Prompt → 结构化 JSON | ≤10s（异步） |
| 3 | 对话练习 | P0-3 | Chat | WebSocket 流式 + 多轮 | <2s 首 token |
| 4 | 日终小结 | P0-4 | Dashboard | 多步推理（需聚合多个数据源） | ≤30s（异步） |
| 5 | 引导对话 | P0-5 | Path | 多轮对话 + 工具调用 | <3s/轮 |
| 6 | 起点分析 | P0-5 | Path | 单次 Prompt → 结构化 JSON | ≤15s（异步） |
| 7 | 路径生成 | P0-5 | Path | 单次 Prompt → 结构化 JSON | ≤15s（异步） |
| 8 | 路径自适应 | P0-5 | Path | 多步推理（需分析多维数据 → 决策） | ≤30s（异步） |
| 9 | 跨领域概念关联 | P1-3 | Concept | 单次 Prompt → 结构化 JSON | ≤15s（异步） |
| 10 | 费曼挑战 | P1-1 | Capture | 单次 Prompt → 评估报告 | ≤30s（异步） |
| 11 | 报告生成 | P1-4 | Dashboard | 单次 Prompt → 结构化 JSON | ≤30s（异步） |
| 12 | 数字人语音交互 | P1-6 | DigitalHuman | WebSocket 流式 + STT→LLM→TTS | <1s 全链路 |
| 13 | 数字人表情系统 | P1-6 | DigitalHuman | LLM 语义分析 → 表情指令 | <500ms |

### 2.2 分类判定标准

**核心判定维度**：该 LLM 交互是否需要 LLM 在多步推理中**自主决定调用哪些工具**？

```
                    ┌──────────────────────────────┐
                    │     LLM 交互点分类决策树       │
                    └──────────────────────────────┘
                               │
                    是否需要 LLM 自主调用工具链？
                         ├─ 是 ─┐
                         │      ↓
                         │   需要实时流式传输？
                         │      ├─ 是 → 架构不匹配（留 FastAPI WS）
                         │      └─ 否 → 适合 Agent Loop
                         │
                         └─ 否 → 单次 Prompt（留 FastAPI）
```

### 2.3 三类归属

| 类别 | 数量 | 交互点编号 | 特征 |
|------|:--:|---------|------|
| **A. 适合 Agent Loop** | 3 | #4, #5, #8 | LLM 需多步推理、自主调用工具、流程不可预编码 |
| **B. 架构不匹配** | 3 | #3, #12, #13 | 需要 WebSocket 流式传输或实时渲染，Agent Loop 无法支撑 |
| **C. 保留 FastAPI** | 7 | #1, #2, #6, #7, #9, #10, #11 | 单次 Prompt → 结构化输出，Agent Loop 是过度设计 |

---

## 3. 分类详细分析

### 3.1 A 类：适合 Agent Loop（3 项）

#### #4 日终小结（P0-4，Dashboard Module）

| 维度 | 分析 |
|------|------|
| **为什么需要 Agent Loop** | 小结不是简单摘要——LLM 需要先拉取今日所有学习事件、计算 DLE、检查 MHI 趋势，然后综合推理生成有洞察力的摘要。流程取决于当日数据的实际内容，无法硬编码。 |
| **触发方式** | Cron 定时（每日 21:00） |
| **需要调用的工具** | `get_learning_events()`, `calc_dle()`, `get_mhi_status()`, `save_daily_digest()` |
| **LLM 推理示例** | 今日 12 张卡片正确率 85% → 对话练习 3 分钟卡顿 2 次 → MHI 0.72 稳定 → 推理：听力速度是主要卡点 → 建议明天重点复习敬语体系 |
| **Provider** | GPT-4o（小结质量要求高） |
| **延迟容忍** | ≤30s（异步任务） |

#### #5 引导对话（P0-5，Path Module）

| 维度 | 分析 |
|------|------|
| **为什么需要 Agent Loop** | 5 分钟多轮对话收集学习目标，LLM 需根据用户回答动态决定追问方向。问题序列取决于用户回答内容，无法预设固定问卷。 |
| **触发方式** | 用户主动发起（新用户注册后） |
| **需要调用的工具** | `get_user_cards()`, `assess_level()`, `save_onboarding_result()`, `generate_path()` |
| **LLM 推理示例** | 用户说"N4 水平" → LLM 决定查询已有卡片验证 → 发现 23 张日语卡片正确率 72% → 确认水平 → 追问使用场景 → 用户说"工作开会" → 生成商务日语路径 |
| **Provider** | GPT-4o（对话质量直接影响用户体验） |
| **延迟容忍** | <3s/轮 |

#### #8 路径自适应（P0-5，Path Module）

| 维度 | 分析 |
|------|------|
| **为什么需要 Agent Loop** | 当 MHI 下降或连续偏离计划时，LLM 需综合分析进度曲线、卡顿点、MHI 趋势等多个维度数据，自主决策调整方向。调整策略因情况而异，无法穷举所有分支。 |
| **触发方式** | 事件驱动（MHI 下降 / 连续 3 天偏离计划） |
| **需要调用的工具** | `get_path_progress()`, `get_struggle_areas()`, `get_mhi_trend()`, `update_path()` |
| **LLM 推理示例** | MHI 从 0.8 降至 0.45 → 拉取卡顿数据 → 听力速度是主要瓶颈 → 决定插入一周听力专项训练 → 更新路径 |
| **Provider** | GPT-4o（决策质量影响学习效果） |
| **延迟容忍** | ≤30s（异步任务） |

### 3.2 B 类：架构不匹配（3 项）

#### #3 对话练习（P0-3，Chat Module）

| 维度 | 分析 |
|------|------|
| **为什么不适合** | 需要 WebSocket 双向流 + 流式 LLM 响应（首 token <2s）+ TTS 实时合成。nanobot 的 CLI/Gateway 模式无法提供 WebSocket 流式传输，且每轮 Agent Loop 迭代增加 1-3s 延迟。 |
| **保留位置** | FastAPI WebSocket + `chat_service.py` |
| **现有方案** | 已有完整的 Session Manager + Scenario Engine + Correction Engine |

#### #12 数字人语音交互（P1-6，DigitalHuman Module）

| 维度 | 分析 |
|------|------|
| **为什么不适合** | STT→LLM→TTS 全链路需 <1s，且需 WS 推送 `avatar_speak` / `avatar_expression` 指令。Agent Loop 的多步迭代延迟无法接受。 |
| **保留位置** | FastAPI WebSocket + `digital_human_service.py` |
| **现有方案** | 复用 Chat WS + Web Speech API + Edge TTS 流式输出 |

#### #13 数字人表情系统（P1-6，DigitalHuman Module）

| 维度 | 分析 |
|------|------|
| **为什么不适合** | 表情切换需与 Three.js VRM 渲染器帧同步（<500ms），且表情由对话语义实时推导。Agent Loop 的迭代式推理无法满足实时性。 |
| **保留位置** | 前端 ExpressionEngine + WS 指令 |
| **现有方案** | 规则映射表（对话语义 → VRM BlendShape） |

### 3.3 C 类：保留 FastAPI 单次 Prompt（7 项）

这些交互点的共同特征：**单次 Prompt → 结构化 JSON 输出**，LLM 不需要自主调用工具，用 Agent Loop 是杀鸡用牛刀。

| # | 交互点 | Prompt 模式 | 输出格式 | 现有实现 |
|---|--------|-----------|---------|---------|
| 1 | 概念提取 | 输入文本 → 提取 ≥3 概念 + 摘要 | `[{concept, definition, domain}]` | `capture_service.py` → Celery Worker |
| 2 | 卡片生成 | 概念 + 领域模板 → 生成正反面卡片 | `{front, back, card_type}` | `memory_service.py` → Celery Worker |
| 6 | 起点分析 | 用户背景信息 → 生成起点报告 | `{level, strengths, gaps, recommendation}` | `path_service.py` |
| 7 | 路径生成 | 起点报告 + 模板 → 里程碑序列 | `[{milestone, duration, focus}]` | `path_service.py` |
| 9 | 跨领域概念关联 | 两个概念定义 → 类比/对比关系 | `{relation_type, analogy, weight}` | `concept_graph_service.py` |
| 10 | 费曼挑战 | 用户输出 + 参考材料 → 评估报告 | `{score, gaps, suggestions}` | `capture_service.py` |
| 11 | 报告生成 | 周期学习数据 → 进度报告 | `{summary, trends, recommendations}` | `dashboard_service.py` |

---

## 4. 集成方案对比

### 4.1 方案 A：nanobot 作为 Sidecar 独立服务

```
┌─────────────────────────────────────────────────────────────────┐
│                        Artifex                                   │
│                                                                 │
│  ┌──────────────┐         ┌──────────────────────┐             │
│  │  PWA 前端     │ ←WS/HTTP→│     FastAPI 后端      │             │
│  │  React PWA   │         │  (REST + WebSocket)  │             │
│  └──────────────┘         │                      │             │
│                           │  Auth/Capture/Memory │             │
│                           │  Chat/Path/Dashboard │             │
│                           │  DigitalHuman        │             │
│                           └──────────┬───────────┘             │
│                                      │ HTTP JSON               │
│                           ┌──────────┴───────────┐             │
│                           │   nanobot Sidecar    │             │
│                           │   (Docker 容器)       │             │
│                           │                      │             │
│                           │  Agent Loop Engine   │             │
│                           │  Cron Scheduler      │             │
│                           │  Skills (HTTP 调用)   │             │
│                           │  Provider Router     │             │
│                           └──────────┬───────────┘             │
│                                      │                         │
│                           ┌──────────┴───────────┐             │
│                           │   LLM Provider API   │             │
│                           │  (OpenAI / Claude)   │             │
│                           └──────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

**通信方式**：FastAPI ↔ nanobot 通过 HTTP JSON 通信，FastAPI 暴露内部数据接口作为 nanobot 的 Skills。

**优势**：
- Agent Loop 零开发成本，nanobot 已实现
- Cron 内置，省去 Celery Beat 配置
- nanobot 源码可读，便于理解 Agent Loop 实现

**劣势**：
- 多一个服务进程，多一层 HTTP 调用延迟（~20-50ms/次）
- nanobot 的 Cron/Memory/Provider 与 Artifex 现有 Celery/Redis/LLM Router **大量功能重叠**
- 双 AI 编排层维护成本高——两个系统都要维护 LLM 路由、成本追踪、错误处理
- Skills 通过 HTTP 调用 FastAPI，增加网络开销和故障点

### 4.2 方案 B：FastAPI 内建轻量 Agent Loop（推荐）

```
┌─────────────────────────────────────────────────────────────────┐
│                        Artifex                                   │
│                                                                 │
│  ┌──────────────┐         ┌──────────────────────────────────┐ │
│  │  PWA 前端     │ ←WS/HTTP→│         FastAPI 后端              │ │
│  │  React PWA   │         │                                  │ │
│  └──────────────┘         │  ┌────────────────────────────┐  │ │
│                           │  │     Agent Loop Module       │  │ │
│                           │  │  (ai/agent_loop.py ~200行)  │  │ │
│                           │  │                            │  │ │
│                           │  │  run_agent_loop()          │  │ │
│                           │  │    ├─ LLM Router (复用)     │  │ │
│                           │  │    ├─ Tool Registry         │  │ │
│                           │  │    └─ Cost Tracker (复用)   │  │ │
│                           │  └────────────┬───────────────┘  │ │
│                           │               │ 调用              │ │
│                           │  ┌────────────┴───────────────┐  │ │
│                           │  │   Tools (内部函数直调)      │  │ │
│                           │  │  get_learning_events()     │  │ │
│                           │  │  calc_dle()                │  │ │
│                           │  │  get_mhi_status()          │  │ │
│                           │  │  get_path_progress()       │  │ │
│                           │  │  update_path()             │  │ │
│                           │  │  ...                       │  │ │
│                           │  └────────────────────────────┘  │ │
│                           │                                  │ │
│                           │  Auth/Capture/Memory/Chat/Path   │ │
│                           │  Dashboard/DigitalHuman          │ │
│                           └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**通信方式**：Agent Loop 作为 FastAPI 内部模块，工具函数直接在进程内调用，零网络开销。

**优势**：
- 零新增服务，零新增部署复杂度
- 工具函数直接调用内部 Service，无 HTTP 开销
- 复用现有 LLM Router / Cost Tracker / 数据库 / Celery
- 代码量极小（~200 行），完全可控
- 单一 AI 编排层，无功能重叠

**劣势**：
- Agent Loop 需自行实现（但参考 nanobot 源码，~200 行足够）
- 无内置 Cron（但已有 Celery Beat 替代）

### 4.3 方案选型矩阵

| 评估维度 | 方案 A (nanobot Sidecar) | 方案 B (内建 Agent Loop) |
|---------|:-----------------------:|:-----------------------:|
| 开发成本 | 低（零开发） | 低（~200 行） |
| 部署复杂度 | 高（+1 容器） | 零（无新增） |
| 调用延迟 | +20-50ms/次 HTTP | 零（进程内调用） |
| 功能重叠 | 严重（Cron/Memory/Provider） | 无 |
| 维护成本 | 高（双 AI 编排层） | 低（单一编排层） |
| 可控性 | 中（受 nanobot 约束） | 高（完全自控） |
| LLM Router | 重复建设 | 复用现有 |
| Cost Tracker | 重复建设 | 复用现有 |
| 错误处理 | 跨服务边界复杂 | 进程内统一处理 |
| 扩展性 | 中 | 高 |

**决策**：采用方案 B。核心原因——Artifex 已有完整的 AI 基础设施（FastAPI + Celery + Redis + LLM Router + Cost Tracker），引入 nanobot 不是填补空白，而是引入功能重叠的第二个 AI 编排层。

---

## 5. Agent Loop 模块详细设计

### 5.1 模块定位

```
backend/app/ai/
├── llm.py                # LLM Router（已有）
├── embedding.py          # Embedding 服务（已有）
├── stt.py                # 语音识别（已有）
├── tts.py                # 语音合成（已有）
├── cost_tracker.py       # Token 用量追踪（已有）
├── agent_loop.py         # ⭐ 新增：Agent Loop 引擎
├── agent_tools.py        # ⭐ 新增：工具函数注册
└── agent_prompts.py      # ⭐ 新增：Agent System Prompts
```

### 5.2 Agent Loop 核心实现

```python
# backend/app/ai/agent_loop.py

"""
轻量 Agent Loop 引擎。
参考 nanobot 的 Agent Loop 设计，但完全复用 Artifex 现有基础设施。
核心流程：LLM 推理 → 判断是否调用工具 → 调用 → 注入结果 → 继续推理。
"""

from typing import Any, Callable
from pydantic import BaseModel
from app.ai.llm import llm_router          # 复用现有 LLM Router
from app.ai.cost_tracker import cost_tracker  # 复用现有成本追踪

import logging
logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """工具定义——描述一个可被 LLM 调用的函数"""
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema
    function: Callable           # 实际执行的 Python 函数


class AgentLoopResult(BaseModel):
    """Agent Loop 执行结果"""
    content: str                 # LLM 最终回复
    tool_calls: list[dict]       # 工具调用历史（审计用）
    iterations: int              # 实际迭代次数
    total_tokens: int            # Token 总消耗


async def run_agent_loop(
    system_prompt: str,
    user_message: str,
    tools: dict[str, ToolDefinition],
    max_iterations: int = 10,
    model: str = "gpt-4o",
    context: dict | None = None,
) -> AgentLoopResult:
    """
    执行 Agent Loop。

    参数：
        system_prompt: 系统提示词，定义 Agent 的角色和任务
        user_message: 用户消息或任务描述
        tools: 可用工具字典 {tool_name: ToolDefinition}
        max_iterations: 最大迭代次数（防止无限循环）
        model: 使用的 LLM 模型
        context: 额外上下文（如 user_id 等）

    返回：
        AgentLoopResult: 包含最终回复、工具调用历史、Token 消耗
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # 如果有额外上下文，注入到 system prompt 之后
    if context:
        messages.insert(1, {
            "role": "system",
            "content": f"上下文信息：{context}"
        })

    tool_call_history = []
    total_tokens = 0

    for iteration in range(max_iterations):
        # 构造 OpenAI function calling 格式的工具定义
        tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in tools.values()
        ]

        # 调用 LLM（复用现有 LLM Router）
        response = await llm_router.chat(
            messages=messages,
            model=model,
            tools=tool_schemas if tool_schemas else None,
            tool_choice="auto" if tool_schemas else None,
        )

        total_tokens += response.usage.total_tokens

        # 如果 LLM 决定不调用工具，返回最终回复
        if not response.tool_calls:
            return AgentLoopResult(
                content=response.content,
                tool_calls=tool_call_history,
                iterations=iteration + 1,
                total_tokens=total_tokens,
            )

        # 执行 LLM 请求的工具调用
        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            logger.info(
                f"Agent Loop iteration {iteration + 1}: "
                f"calling tool '{tool_name}' with args: {tool_args}"
            )

            if tool_name not in tools:
                tool_result = f"Error: tool '{tool_name}' not found"
            else:
                try:
                    tool_result = await tools[tool_name].function(**tool_args)
                except Exception as e:
                    tool_result = f"Error executing tool '{tool_name}': {e}"
                    logger.error(f"Tool execution error: {e}", exc_info=True)

            tool_call_history.append({
                "iteration": iteration + 1,
                "tool": tool_name,
                "args": tool_args,
                "result": str(tool_result)[:500],  # 截断防止上下文爆炸
            })

            # 将工具结果注入对话上下文
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result),
            })

        # 记录 LLM 的 assistant 消息（含 tool_calls）
        messages.append({
            "role": "assistant",
            "content": response.content or "",
            "tool_calls": response.tool_calls,
        })

    # 达到最大迭代次数，强制返回
    logger.warning(
        f"Agent Loop reached max iterations ({max_iterations}), "
        f"forcing return"
    )
    return AgentLoopResult(
        content="达到最大推理迭代次数，请稍后重试或简化任务。",
        tool_calls=tool_call_history,
        iterations=max_iterations,
        total_tokens=total_tokens,
    )
```

### 5.3 工具函数注册

```python
# backend/app/ai/agent_tools.py

"""
Agent Loop 可用工具函数注册。
每个工具直接调用内部 Service 层函数，零网络开销。
"""

from app.ai.agent_loop import ToolDefinition
from app.services.dashboard_service import DashboardService
from app.services.path_service import PathService
from app.services.memory_service import MemoryService


# ===== Dashboard 相关工具（日终小结用）=====

async def get_learning_events(user_id: str, date: str) -> dict:
    """获取用户指定日期的学习事件列表"""
    service = DashboardService()
    events = await service.get_daily_events(user_id, date)
    return {
        "events": [
            {
                "type": e.type,
                "count": e.count,
                "accuracy": e.accuracy,
                "duration_seconds": e.duration_seconds,
            }
            for e in events
        ]
    }


async def calc_dle(user_id: str, date: str) -> dict:
    """计算用户指定日期的日均学习效能（DLE）"""
    service = DashboardService()
    dle = await service.calculate_dle(user_id, date)
    return {"dle": dle}


async def get_mhi_status(user_id: str) -> dict:
    """获取用户动力健康度（MHI）当前状态"""
    service = DashboardService()
    mhi = await service.get_mhi(user_id)
    return {
        "score": mhi.score,
        "level": mhi.level,
        "trend": mhi.trend,
        "streak_days": mhi.streak_days,
    }


async def save_daily_digest(user_id: str, digest: dict) -> dict:
    """保存日终小结"""
    service = DashboardService()
    result = await service.save_digest(user_id, digest)
    return {"success": True, "digest_id": result.id}


# ===== Path 相关工具（引导对话 + 路径自适应用）=====

async def get_user_cards(user_id: str, domain: str = None) -> dict:
    """获取用户的卡片统计信息"""
    service = MemoryService()
    stats = await service.get_card_stats(user_id, domain)
    return {
        "total_cards": stats.total,
        "due_cards": stats.due,
        "accuracy": stats.accuracy,
        "domain": domain,
    }


async def assess_level(user_id: str, domain: str) -> dict:
    """评估用户在指定领域的学习水平"""
    service = PathService()
    level = await service.assess_user_level(user_id, domain)
    return {
        "domain": domain,
        "estimated_level": level.estimated,
        "confidence": level.confidence,
        "evidence": level.evidence,
    }


async def save_onboarding_result(user_id: str, result: dict) -> dict:
    """保存引导对话结果"""
    service = PathService()
    saved = await service.save_onboarding(user_id, result)
    return {"success": True, "onboarding_id": saved.id}


async def generate_path(user_id: str, starting_point: dict) -> dict:
    """基于起点报告生成学习路径"""
    service = PathService()
    path = await service.generate_learning_path(user_id, starting_point)
    return {"path_id": path.id, "milestones": len(path.milestones)}


async def get_path_progress(user_id: str) -> dict:
    """获取用户当前学习路径进度"""
    service = PathService()
    progress = await service.get_current_progress(user_id)
    return {
        "current_milestone": progress.current_milestone,
        "completion_rate": progress.completion_rate,
        "overdue_milestones": progress.overdue,
        "last_updated": progress.last_updated,
    }


async def get_struggle_areas(user_id: str) -> dict:
    """获取用户学习卡顿点"""
    service = PathService()
    areas = await service.get_struggle_areas(user_id)
    return {
        "struggle_areas": [
            {"topic": a.topic, "severity": a.severity, "domain": a.domain}
            for a in areas
        ]
    }


async def get_mhi_trend(user_id: str, days: int = 14) -> dict:
    """获取用户近 N 天的 MHI 趋势"""
    service = DashboardService()
    trend = await service.get_mhi_history(user_id, days)
    return {
        "trend": trend.scores,
        "average": trend.average,
        "direction": trend.direction,  # "rising" / "stable" / "falling"
    }


async def update_path(user_id: str, adjustment: dict) -> dict:
    """更新用户学习路径（插入/删除/修改里程碑）"""
    service = PathService()
    result = await service.adjust_path(user_id, adjustment)
    return {
        "success": True,
        "adjusted": result.adjusted,
        "new_milestones": result.new_milestones,
    }


# ===== 工具注册表 =====

DASHBOARD_TOOLS = {
    "get_learning_events": ToolDefinition(
        name="get_learning_events",
        description="获取用户指定日期的所有学习事件（卡片复习、对话练习、内容捕获等）",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
                "date": {"type": "string", "description": "日期 YYYY-MM-DD"},
            },
            "required": ["user_id", "date"],
        },
        function=get_learning_events,
    ),
    "calc_dle": ToolDefinition(
        name="calc_dle",
        description="计算用户指定日期的日均学习效能 DLE",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["user_id", "date"],
        },
        function=calc_dle,
    ),
    "get_mhi_status": ToolDefinition(
        name="get_mhi_status",
        description="获取用户动力健康度 MHI 的当前状态、等级和趋势",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
        function=get_mhi_status,
    ),
    "save_daily_digest": ToolDefinition(
        name="save_daily_digest",
        description="保存生成的日终小结",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "digest": {
                    "type": "object",
                    "description": "日终小结内容，包含 summary, highlights, suggestions, dle, mhi",
                },
            },
            "required": ["user_id", "digest"],
        },
        function=save_daily_digest,
    ),
}

PATH_TOOLS = {
    "get_user_cards": ToolDefinition(
        name="get_user_cards",
        description="获取用户的卡片统计信息（总数、待复习数、正确率）",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "domain": {"type": "string", "description": "领域: language/humanities/skill"},
            },
            "required": ["user_id"],
        },
        function=get_user_cards,
    ),
    "assess_level": ToolDefinition(
        name="assess_level",
        description="评估用户在指定领域的学习水平",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "domain": {"type": "string"},
            },
            "required": ["user_id", "domain"],
        },
        function=assess_level,
    ),
    "save_onboarding_result": ToolDefinition(
        name="save_onboarding_result",
        description="保存引导对话收集的结果（学习目标、水平、偏好场景）",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "result": {"type": "object"},
            },
            "required": ["user_id", "result"],
        },
        function=save_onboarding_result,
    ),
    "generate_path": ToolDefinition(
        name="generate_path",
        description="基于起点报告生成学习路径",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "starting_point": {"type": "object"},
            },
            "required": ["user_id", "starting_point"],
        },
        function=generate_path,
    ),
    "get_path_progress": ToolDefinition(
        name="get_path_progress",
        description="获取用户当前学习路径的进度",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
        function=get_path_progress,
    ),
    "get_struggle_areas": ToolDefinition(
        name="get_struggle_areas",
        description="获取用户学习中的卡顿点/薄弱环节",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
        function=get_struggle_areas,
    ),
    "get_mhi_trend": ToolDefinition(
        name="get_mhi_trend",
        description="获取用户近 N 天的 MHI 趋势数据",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "days": {"type": "integer", "default": 14},
            },
            "required": ["user_id"],
        },
        function=get_mhi_trend,
    ),
    "update_path": ToolDefinition(
        name="update_path",
        description="更新用户学习路径（插入复习周、调整里程碑等）",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "adjustment": {"type": "object"},
            },
            "required": ["user_id", "adjustment"],
        },
        function=update_path,
    ),
}
```

### 5.4 Agent System Prompts

```python
# backend/app/ai/agent_prompts.py

"""
Agent Loop 各任务的 System Prompt。
每个 prompt 定义 Agent 的角色、任务目标、可用工具使用规则。
"""

DAILY_DIGEST_PROMPT = """你是 Artifex 学习平台的日终小结助手。

你的任务是为用户生成今日学习小结，步骤如下：
1. 调用 get_learning_events 获取用户今日所有学习事件
2. 调用 calc_dle 计算今日日均学习效能
3. 调用 get_mhi_status 获取当前动力健康度
4. 综合以上数据，生成一份有洞察力的小结，包含：
   - summary: 今日学习概况（2-3 句话）
   - highlights: 今日亮点（1-3 条）
   - suggestions: 明日建议（1-2 条，基于今日数据有针对性地建议）
   - dle: 今日 DLE 数值
   - mhi: 当前 MHI 数值
5. 调用 save_daily_digest 保存小结

要求：
- 小结要有洞察力，不是简单罗列数据
- 建议要具体、可执行，基于今日实际数据
- 如果某领域今天没有学习事件，也要提及
- 语气温暖但不过度夸张
"""

ONBOARDING_PROMPT = """你是 Artifex 学习平台的学习顾问。

你的任务是通过 5 分钟对话了解新用户的学习目标。对话规则：
1. 每次只问一个问题，自然引导对话
2. 需要收集的信息：
   - 学习领域（语言/人文/技能）
   - 当前水平（可调用 assess_level 验证用户自评）
   - 学习目标（考试/工作/旅行/兴趣等）
   - 偏好场景（如日语：商务会议/日常交流/旅行）
   - 每日可投入时间
3. 可调用 get_user_cards 查看用户已有卡片了解基础
4. 收集完毕后，调用 save_onboarding_result 保存结果
5. 然后调用 generate_path 生成初始学习路径
6. 最后向用户简要介绍生成的路径

要求：
- 对话自然流畅，不要像填表
- 根据用户回答灵活调整追问方向
- 如果用户表达不确定，给出选项帮助决策
"""

PATH_ADAPTIVE_PROMPT = """你是 Artifex 学习平台的路径调整顾问。

触发条件：用户 MHI 下降或连续偏离学习计划。

你的任务是分析原因并调整学习路径：
1. 调用 get_path_progress 获取当前路径进度
2. 调用 get_struggle_areas 获取卡顿点
3. 调用 get_mhi_trend 获取近 14 天 MHI 趋势
4. 综合分析：
   - MHI 下降的可能原因（进度滞后/难度过高/缺乏正反馈等）
   - 主要卡顿领域和知识点
   - 是否需要插入复习周、降低难度、或调整里程碑
5. 调用 update_path 执行路径调整
6. 返回调整说明（调整了什么、为什么调整、预期效果）

要求：
- 调整要有数据依据，不要随意改动
- 优先做"减法"（减少负荷）而非"加法"
- 调整说明要让用户理解原因，避免突然变化让用户困惑
"""
```

### 5.5 任务调度集成

#### 日终小结（Cron 触发）

```python
# backend/app/workers/daily_digest_agent.py

"""
日终小结 Agent 任务。
由 Celery Beat 每日 21:00 触发，为所有活跃用户生成小结。
"""

from celery import shared_task
from app.ai.agent_loop import run_agent_loop
from app.ai.agent_tools import DASHBOARD_TOOLS
from app.ai.agent_prompts import DAILY_DIGEST_PROMPT
from app.services.user_service import UserService


@shared_task(bind=True, max_retries=3)
def generate_daily_digest_for_all_users(self):
    """为所有活跃用户生成日终小结（Celery Beat 定时触发）"""
    user_service = UserService()
    active_users = user_service.get_active_user_ids()

    for user_id in active_users:
        generate_daily_digest_for_user.delay(str(user_id))


@shared_task(bind=True, max_retries=3)
def generate_daily_digest_for_user(self, user_id: str):
    """为单个用户生成日终小结"""
    import asyncio
    from datetime import date

    async def _run():
        result = await run_agent_loop(
            system_prompt=DAILY_DIGEST_PROMPT,
            user_message=f"请为用户 {user_id} 生成 {date.today().isoformat()} 的日终小结",
            tools=DASHBOARD_TOOLS,
            max_iterations=8,
            model="gpt-4o",
            context={"user_id": user_id, "date": date.today().isoformat()},
        )
        return result

    try:
        result = asyncio.run(_run())
        # 记录 Token 消耗到成本追踪
        cost_tracker.record(
            user_id=user_id,
            task="daily_digest",
            tokens=result.total_tokens,
            tool_calls=result.iterations,
        )
    except Exception as e:
        # Celery 自动重试
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

#### 路径自适应（事件驱动）

```python
# backend/app/workers/path_adaptive_agent.py

"""
路径自适应 Agent 任务。
由 Dashboard MHI 监控触发，当 MHI 下降或连续偏离计划时执行。
"""

from celery import shared_task
from app.ai.agent_loop import run_agent_loop
from app.ai.agent_tools import PATH_TOOLS
from app.ai.agent_prompts import PATH_ADAPTIVE_PROMPT


@shared_task(bind=True, max_retries=3)
def adjust_learning_path(self, user_id: str, trigger: str, trigger_data: dict):
    """
    路径自适应调整。

    参数：
        user_id: 用户 ID
        trigger: 触发原因 ("mhi_drop" / "plan_deviation" / "streak_break")
        trigger_data: 触发数据 (如 MHI 变化幅度、偏离天数等)
    """
    import asyncio

    async def _run():
        result = await run_agent_loop(
            system_prompt=PATH_ADAPTIVE_PROMPT,
            user_message=(
                f"用户 {user_id} 触发路径调整。\n"
                f"触发原因: {trigger}\n"
                f"触发数据: {trigger_data}\n"
                f"请分析原因并调整学习路径。"
            ),
            tools=PATH_TOOLS,
            max_iterations=8,
            model="gpt-4o",
            context={"user_id": user_id, "trigger": trigger},
        )
        return result

    try:
        result = asyncio.run(_run())
        # 推送通知给用户
        notify_user_path_adjusted.delay(user_id, result.content)
    except Exception as e:
        raise self.retry(exc=e, countdown=300 * (2 ** self.request.retries))


@shared_task
def notify_user_path_adjusted(user_id: str, adjustment_summary: str):
    """通知用户路径已调整"""
    # 通过 WebSocket 推送或站内信通知
    pass
```

#### 引导对话（用户发起，WebSocket 适配）

```python
# backend/app/api/v1/path.py (扩展)

"""
引导对话 Agent。
用户发起后通过 WebSocket 多轮交互。
Agent Loop 在每轮对话中执行，LLM 决定是否调用工具或继续对话。
"""

from fastapi import APIRouter, WebSocket
from app.ai.agent_loop import run_agent_loop
from app.ai.agent_tools import PATH_TOOLS
from app.ai.agent_prompts import ONBOARDING_PROMPT

router = APIRouter()


@router.websocket("/ws/v1/onboarding")
async def onboarding_agent(ws: WebSocket):
    """引导对话 WebSocket 端点"""
    await ws.accept()

    # 获取用户信息
    token = ws.query_params.get("token")
    user_id = verify_jwt(token)

    conversation_history = []

    # 首轮：Agent 主动开场
    first_result = await run_agent_loop(
        system_prompt=ONBOARDING_PROMPT,
        user_message="新用户注册完成，请开始引导对话。",
        tools=PATH_TOOLS,
        max_iterations=5,
        context={"user_id": str(user_id)},
    )
    await ws.send_json({"type": "agent_message", "content": first_result.content})
    conversation_history.append({"role": "assistant", "content": first_result.content})

    # 多轮对话循环
    while True:
        msg = await ws.receive_json()
        if msg.get("type") == "end":
            break

        user_text = msg.get("content", "")
        conversation_history.append({"role": "user", "content": user_text})

        # 每轮对话执行一次 Agent Loop
        result = await run_agent_loop(
            system_prompt=ONBOARDING_PROMPT,
            user_message=user_text,
            tools=PATH_TOOLS,
            max_iterations=5,
            context={"user_id": str(user_id)},
        )
        await ws.send_json({"type": "agent_message", "content": result.content})
        conversation_history.append({"role": "assistant", "content": result.content})

    await ws.close()
```

---

## 6. 数据流与调用时序

### 6.1 日终小结时序

```
21:00  Celery Beat 触发
  │
  ↓
Celery Worker: generate_daily_digest_for_all_users()
  │
  ├─ 查询所有活跃用户 ID
  │
  └─ 为每个用户派发子任务 ↓

generate_daily_digest_for_user(user_id)
  │
  ↓
run_agent_loop(
  system_prompt=DAILY_DIGEST_PROMPT,
  tools=DASHBOARD_TOOLS
)
  │
  ├─ Iteration 1: LLM 推理
  │    → 决定调用 get_learning_events(user_id, today)
  │    ← 返回: [{type:"card_review", count:12, accuracy:0.85}, ...]
  │
  ├─ Iteration 2: LLM 推理
  │    → 决定调用 calc_dle(user_id, today)
  │    ← 返回: {dle: 2.4}
  │
  ├─ Iteration 3: LLM 推理
  │    → 决定调用 get_mhi_status(user_id)
  │    ← 返回: {score:0.72, level:"healthy", trend:"stable"}
  │
  ├─ Iteration 4: LLM 综合推理
  │    → 生成小结内容
  │    → 决定调用 save_daily_digest(user_id, {summary, highlights, ...})
  │    ← 返回: {success: true, digest_id: "xxx"}
  │
  └─ Iteration 5: LLM 确认完成，返回最终回复
       ↓
  cost_tracker 记录 Token 消耗
```

### 6.2 路径自适应时序

```
MHI 监控检测到下降 (0.8 → 0.45)
  │
  ↓
Celery: adjust_learning_path(user_id, "mhi_drop", {from:0.8, to:0.45})
  │
  ↓
run_agent_loop(
  system_prompt=PATH_ADAPTIVE_PROMPT,
  tools=PATH_TOOLS
)
  │
  ├─ Iteration 1: LLM 推理
  │    → 调用 get_path_progress(user_id)
  │    ← {current_milestone:"W5-8", completion:0.6, overdue:2}
  │
  ├─ Iteration 2: LLM 推理
  │    → 调用 get_struggle_areas(user_id)
  │    ← [{topic:"敬语体系", severity:"high"}, {topic:"听力速度", severity:"medium"}]
  │
  ├─ Iteration 3: LLM 推理
  │    → 调用 get_mhi_trend(user_id, days=14)
  │    ← {trend:[0.8,0.75,0.6,0.45,...], direction:"falling"}
  │
  ├─ Iteration 4: LLM 综合分析
  │    → MHI 连续下降 + 听力速度卡顿 → 决定插入听力专项复习周
  │    → 调用 update_path(user_id, {action:"insert_review_week", focus:"听力速度"})
  │    ← {success:true, adjusted:true}
  │
  └─ Iteration 5: LLM 生成调整说明
       ↓
  notify_user_path_adjusted(user_id, "已为您插入一周听力专项训练...")
```

---

## 7. 成本影响分析

### 7.1 Agent Loop 额外 Token 消耗

Agent Loop 相比单次 Prompt 模式，额外消耗来自：
- 每次工具调用结果注入上下文（~200-500 tokens/次）
- System Prompt 中工具定义（~800-1200 tokens 固定开销）
- 多轮迭代累计的对话历史

| 任务 | 迭代次数 | 预估 Token/次 | 日触发频次 | 日额外 Token |
|------|---------|-------------|-----------|-------------|
| 日终小结 | 4-6 | ~3,000 | 1 次/用户 | ~3,000 |
| 引导对话 | 5-8 | ~2,500 | 1 次（新用户） | ~2,500（一次性） |
| 路径自适应 | 4-6 | ~3,500 | ~0.1 次/用户 | ~350 |

### 7.2 成本估算

```
Agent Loop 日均额外成本/用户:
  日终小结:  3,000 tokens × $0.01/1K = $0.03
  路径自适应: 350 tokens × $0.01/1K = $0.0035
  ──────────────────────────────────
  额外日成本: ~$0.034/用户
  额外月成本: ~$1.02/用户

对比原有日成本 ($0.10-0.25/用户)：
  Agent Loop 增加约 14-34% 成本
```

### 7.3 成本控制措施

| 措施 | 说明 | 预估节省 |
|------|------|---------|
| 工具结果截断 | 工具返回结果截断至 500 字符注入上下文 | 30-50% 上下文 Token |
| 迭代次数限制 | `max_iterations=8` 硬上限 | 防止异常消耗 |
| 结果缓存 | 同一用户同日的小结不重复生成 | 100% 重复请求 |
| 低成本模型降级 | 引导对话可用 GPT-4o-mini 降级 | 60-70% 单次成本 |

---

## 8. 风险评估

| 风险 | 等级 | 缓解措施 | 决策节点 |
|------|:--:|---------|:------:|
| Agent Loop 无限循环 | 🟡 | `max_iterations` 硬上限 + 超时检测 | 开发时 |
| 工具调用参数错误 | 🟡 | Pydantic 校验 + try/except 错误注入上下文 | 开发时 |
| LLM 幻觉调用不存在的工具 | 🟡 | 工具名校验 + 错误消息引导 LLM 重试 | 开发时 |
| Token 消耗超预期 | 🟡 | 每次任务记录 Token + 用户日预算硬上限 | W2 |
| 工具结果过大撑爆上下文 | 🟡 | 结果截断至 500 字符 + 旧工具结果摘要压缩 | 开发时 |
| Agent Loop 延迟过长 | 🟡 | 异步 Celery 执行 + 用户端进度提示 | 测试时 |
| 引导对话体验不自然 | 🟡 | Prompt 工程迭代 + A/B 测试不同 prompt | W9-10 |

---

## 9. 与现有技术架构的关系

### 9.1 不需要修改的模块

以下模块完全不受 Agent Loop 引入影响：

- Auth Module — 认证逻辑不变
- Capture Module — 概念提取仍是单次 Prompt
- Memory Module — FSRS 调度和卡片生成不变
- Chat Module — 对话练习仍走 WebSocket 流式
- DigitalHuman Module — 语音交互和表情系统不变
- Concept Graph Module — 概念关联仍是单次 Prompt

### 9.2 需要修改的模块

| 模块 | 修改内容 | 影响范围 |
|------|---------|---------|
| Path Module | `onboarding` 流程改用 Agent Loop；`adaptive_adjuster` 改用 Agent Loop | `path_service.py` + 新增 WS 端点 |
| Dashboard Module | `daily_digest` 改用 Agent Loop | `dashboard_service.py` + Celery Worker |
| AI Layer | 新增 `agent_loop.py`, `agent_tools.py`, `agent_prompts.py` | `ai/` 目录新增 3 个文件 |

### 9.3 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| WS | `/ws/v1/onboarding` | 引导对话 Agent WebSocket |

现有端点不受影响：
- `POST /api/v1/path/onboarding/complete` — 保留，但内部改为调用 Agent Loop
- `GET /api/v1/dashboard/digest` — 保留，读取 Agent 生成的小结

---

## 10. 实施计划

| 阶段 | 内容 | 人天 | 依赖 |
|------|------|:--:|------|
| **Phase 1** | Agent Loop 核心引擎开发（`agent_loop.py`） | 2 | 无 |
| **Phase 2** | 工具函数注册（`agent_tools.py`） | 2 | Phase 1 |
| **Phase 3** | System Prompts 编写 + 调优（`agent_prompts.py`） | 1 | Phase 1 |
| **Phase 4** | 日终小结 Agent 集成（Celery Worker） | 1 | Phase 1-3 |
| **Phase 5** | 路径自适应 Agent 集成（事件驱动） | 1 | Phase 1-3 |
| **Phase 6** | 引导对话 Agent 集成（WebSocket） | 2 | Phase 1-3 |
| **Phase 7** | 测试 + Prompt 调优 | 2 | Phase 4-6 |
| **合计** | | **11** | |

建议在 M3（W9-12）实施，此时 P0 核心功能已稳定，可以在此基础上叠加 Agent Loop 能力。

---

## 11. 总结

### 核心决策

**不引入 nanobot 作为独立服务，在 FastAPI 内部自建轻量 Agent Loop。**

### 决策依据

1. **功能重叠**：nanobot 的 Cron/Memory/Provider 与 Artifex 现有 Celery/Redis/LLM Router 大量重叠，引入后等于维护双 AI 编排层
2. **成本可控**：自建 Agent Loop ~200 行 Python，参考 nanobot 源码实现，完全可控
3. **零网络开销**：工具函数进程内直调，无 HTTP 调用延迟
4. **复用现有设施**：LLM Router、Cost Tracker、数据库、Celery 全部复用

### Agent Loop 适用的 3 项任务

| 任务 | 模式 | 触发方式 | 迭代次数 |
|------|------|---------|---------|
| 日终小结 | 异步 Agent Loop | Cron 21:00 | 4-6 |
| 引导对话 | WS 多轮 Agent Loop | 用户发起 | 5-8/轮 |
| 路径自适应 | 异步 Agent Loop | 事件驱动 | 4-6 |

### 不适用 Agent Loop 的 10 项任务

- 3 项需要实时流式传输（对话练习、数字人语音、表情系统）→ 保留 FastAPI WebSocket
- 7 项单次 Prompt → 结构化输出（概念提取、卡片生成等）→ 保留现有 Celery Worker

---

> 本文档对应 PRD 阶段：技术方案设计。Agent Loop 核心引擎需在 M3（W9-12）完成开发，与 Path Module 和 Dashboard Module 的 Agent 集成同步推进。Prompt 工程需在 Phase 7 测试阶段持续调优。nanobot 源码（github.com/HKUDS/nanobot）作为 Agent Loop 实现的设计参考。

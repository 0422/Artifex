# 📝 更新日志

> 🚧 **待补充** — 此文档正在编写中

## 说明

本文档将按版本记录所有重要的变更。

**格式参考**: [Keep a Changelog](https://keepachangelog.com/)

---

## [Unreleased]

### Added

- 🚧 待补充

### Changed

- 侧边栏自上而下调整为：仪表盘 → 情境对话 → 边缘设备 → 知识库 → 工具库（移动端底部导航同步）
- 「边缘管理」更名为「边缘设备」，页面标题同步

### Fixed

- 🚧 待补充

### Removed

- 工具库下线五张卡片：学习路径、内容捕获、文本统计、英文大小写转换、逐行去重；删除 `PathPage`、`CapturePage`、`ToolPage` 及三个轻量工具组件，工具库仅保留集装箱装载计算器
- 删除 5 分钟引导流程：`OnboardingPage`、`/onboarding` 路由、`pathApi`
- 后端删除 capture / path 模块（路由、schema、service、模型）及 `content_extractor`、`embedding`、`concept_graph_service`
- 数据库迁移 `a1c4e9f06b23`：drop `captures`、`concept_nodes`、`concept_edges`、`learning_paths`、`path_milestones` 五张表，并删除 `cards.source_concept_id`、`user_profiles.onboarding_completed` 两列
- 删除 `llm.extract_concepts` / `generate_cards` / `generate_learning_path` 及对应三个 prompt
- 配置项删除 `OPENAI_EMBEDDING_MODEL`、`DAILY_TOKEN_BUDGET_EMBEDDING`；升级前需同步清理本地 `.env`，残留 key 会因 `extra=forbid` 导致后端启动失败

---

**版本历史**:

- **M1** (2026-08-15) — 框架搭建：数据模型、Auth模块、前后端脚手架
- **M2** (2026-08-15) — 场景对话闭环：对话流、消息持久化
- **M3** (2026-08-15) — 流式语音与数字人：语音对话、虚拟形象
- **M4** (2026-08-16) — 知识库：分类树、场景管理（知识图谱已下线）
- **M5** (2026-08-17) — 工具库：工具注册表、iframe 隔离的单页工具（现仅保留集装箱装载计算器）
- **M6** (待定) — 世势洞察

---

**相关文档**:

- [开发阶段文档](../design/phases/) — 各阶段详细记录

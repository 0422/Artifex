### 教学闭环
个人学习成长类 agent 不是套壳 LLM，其需要的是一个教学闭环，至少涵盖：
> [!clean]- 1、学习者画像
> Student Model：Agent 如何知道你是谁，你的水平
> 【**知识状态建模**】用 BKT（Bayesian Knowledge Tracing）或 IRT（Item Response Theory）对你的每个知识点建立掌握概率
> 【**薄弱点追踪**】记录错误模式，不是"错了什么题"，而是"哪种类型的推理出错"
> 【**学习偏好**】偏好理论推导还是实例驱动？深度优先还是广度优先？

> [!clean]- 2、知识库与内容管理
> - **多模态文档解析**：PDF、Markdown、PPTX、视频字幕等 → 结构化抽取
> - **RAG 检索增强生成**：向量语义搜索 + 知识图谱结构搜索的双路召回
> - **知识图谱构建**：概念实体 → 依赖关系（前置/包含/相关），形成可导航的结构

> [!clean]- 3、教学策略引擎
> 核心问题：当前状态下，下一步该干什么？
> - **自适应难度选择**：基于认知负荷理论，在"舒适区边缘"出题
> - **苏格拉底式引导**：不直接给答案，而是逐步追问
> - **间隔重复调度**：FSRS（Free Spaced Repetition Scheduler）替代传统的 SM-2 算法
> - **学习路径规划**：给定目标和当前状态，生成最优前置依赖路径

> [!clean]- 4、互动与练习生成
> - **自动出题**：选择题、填空题、代码题，支持模仿真题风格
> - **即时反馈与溯源**：错题不仅告诉对错，还引用到原始教材的具体位置
> - **多 Agent 协作解题**：Investigate → Plan → Solve → Check 的多角色推理链

> [!clean]- 5、记忆与持久化
> - **跨会话上下文**：不是每次对话从零开始
> - **学习进度可量化**：掌握度变化曲线、时间投入统计
> - **笔记本系统**：学习过程中产生的笔记、错题、总结自动归入结构化知识库


### 技术栈组成
由此五部分组成的闭环，技术栈分为前端、后端、AI 引擎、学习科学四个层次：

| 前端技术                       | 适用场景           | 备注                         |
|--------------------------|----------------|----------------------------|
| Next.js 16 + React 19    | 功能丰富的 Web 工作台  | DeepTutor、OpenTutor 的选择    |
| Cytoscape.js / D3.js     | 知识图谱可视化        | 概念依赖图的交互式渲染                |
| Tailwind CSS + shadcn/ui | 快速 UI 开发       | 组件化、主题友好                   |
| Streamlit                | 快速原型 / 轻量 Demo | AI Teaching Agent Team 的方案 |

| 后端技术                    | 优势                                 | 典型项目                                         |
|-------------------------|------------------------------------|----------------------------------------------|
| Python FastAPI          | 生态最丰富，LLM/MCP 支持最好                 | DeepTutor、OpenTutor、adaptive-knowledge-graph |
| LangGraph               | 多 Agent 状态机编排，支持 human-in-the-loop | Adaptive Learning Tutor                      |
| LangChain               | RAG pipeline 开箱即用                  | 大多数早期项目                                      |
| CrewAI / Agno / AutoGen | 多 Agent 协作框架                       | AI Teaching Agent Team（Agno）                 |

| AI 引擎层    | 推荐方案                                          | 说明                    |
|-----------|-----------------------------------------------|-----------------------|
| LLM       | GPT-4o / Claude / DeepSeek / 本地 Qwen + Ollama | 多 Provider 可切换，支持离线部署 |
| Embedding | BGE-M3 / Jina / text-embedding-3              | 中英文混合场景 BGE-M3 表现好    |
| 向量数据库     | FAISS / Chroma / Qdrant / OpenSearch          | 本地场景 FAISS；生产 Qdrant  |
| 图数据库      | Neo4j / NetworkX（轻量）                          | 知识图谱存储和遍历             |
| Reranker  | BGE-Reranker-v2                               | 召回后精排，显著提升 RAG 准确率    |

| 学习科学层算法       | 用途          | 成熟度                       |
| ------------- | ----------- | ------------------------- |
| FSRS 4.5      | 间隔重复调度      | Anki 新一代算法，开源成熟           |
| BKT（pyBKT）    | 知识点掌握度建模    | 在教育数据挖掘中广泛验证              |
| IRT（py-irt）   | 题目难度与学生能力建模 | 考试测评行业标准                  |
| LECTOR / LOOM | 知识图谱感知的间隔复习 | 2025 年新论文，OpenTutor 实验性集成 |

### 可参考开源项目

| 高星项目                     | 机构    | 语言                  | 定位                   | 核心亮点                                                                                                                                                                                                  |
| ------------------------ | ----- | ------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DeepTutor                | HKUDS | Python + TypeScript | 最成熟的Agent-Native学习平台 | 五层个性化基板（编排→工具→能力→记忆→画像）；八合一工作台（Chat/Deep Solve/Quiz/Deep Research/Math Animator/Visualize/Co-Writer/Guided Learning）；TutorBot支持15通道交互（Discord/微信/Telegram等）；支持Ollama/LM Studio本地离线部署；Docker一键部署+CLI模式 |
| OpenTutor                | MIT   | Python + TypeScript | 模块化自适应学习工作台          | 12种可组合学习块（笔记/测验/闪卡等）；集成FSRS 4.5+BKT+LOOM（知识图谱感知间隔复习）+认知负荷检测；Canvas LMS集成；支持10+LLM Provider；学习科学理论驱动最深                                                                                                 |
| Adaptive Knowledge Graph | MIT   | —                   | 知识图谱+自适应学习           | 教材自动提取概念→Neo4j知识图谱（PREREQ/COVERS/ASSESS/RELATED四种边）；KG-Aware RAG自动拉入前置概念；BKT+IRT双重建模→Next-Best-Action推荐；本地优先（Ollama Llama3.1 8B + RTX 4070可跑）                                                         |
| Clew                     | MIT   | TypeScript + Python | 学习路径规划               | 目标倒推前置依赖图；Obsidian双向导入/导出；MCP协议桥接（Claude/Cursor可直接读学习图谱）；AI提议结构→人工审查确认→快照回滚机制                                                                                                                         |

| 其他项目                                | 定位             | 亮点                                                                                       |
|-------------------------------------|----------------|------------------------------------------------------------------------------------------|
| AI Teaching Agent Team              | 四Agent协作教学     | Professor + Academic Advisor + Research Librarian + Teaching Assistant，结果自动写入Google Docs |
| Adaptive Learning Tutor (LangGraph) | LangGraph多轮自适应 | 误解分类→自适应追问→human-in-the-loop，代码量小适合学习                                                    |
| DIY-MKG                             | 多语言词汇知识图谱      | 论文级项目，LLM构建个性化多语言词汇图谱+自适应测验                                                              |
| PersonalOS                          | 个人成长框架         | 非纯技术项目，方法论（三层PDCA+四区工作空间），可与上述工具组合使用                                                     |
| human-learning-skill                | 全栈学习CLI Agent  | 需求摸底→定制路线→分步讲解→闭环自测，输出Markdown+导入Obsidian                                                |


### 桌面数字人技术调研

学习场景中的数字人不是"花瓶"，其核心价值是**将AI Agent具象化**——给"有人陪你走"这个设计原则一个可见的载体。以下为技术选型调研结论。

#### 渲染方案对比

| 方案 | 技术栈 | 优势 | 劣势 | 适用场景 |
|------|--------|------|------|---------|
| **VRM (3D)** | Three.js + @pixiv/three-vrm | 3D表现力强、骨骼动画丰富、开源生态好、支持MToon着色器 | 资源占用较高、模型制作门槛高 | 桌面端主力方案 |
| **Live2D (2D)** | PixiJS + live2d-widget | 2D手绘风格、资源轻量、日系审美契合 | 表现力受限、商用授权复杂 | 轻量/移动端备选 |
| **CSS/SVG 拟人** | 纯前端 | 零依赖、极致轻量 | 表现力极弱、无法lip-sync | 降级兜底方案 |

**推荐**：VRM (3D) 为主方案。`@pixiv/three-vrm` 是 Pixiv 开源的 VRM 加载/控制库，基于 Three.js，社区活跃，免费模型资源丰富（VRoid Hub）。

#### 语音交互链路

```
用户语音 → [STT] → 文本 → [LLM] → 回复文本 → [TTS] → 音频流
                                                         ↓
                                              [Lip-Sync 引擎] → 驱动数字人口型/表情
```

| 环节 | 方案 | 延迟 | 备注 |
|------|------|------|------|
| STT | Web Speech API (浏览器原生) | <300ms | 实时转写，但非母语准确率一般 |
| STT | OpenAI Whisper API | 0.5-1.5s | 准确率高，但需网络传输 |
| STT | 本地 Whisper (whisper.cpp) | 200-500ms | 准确率高+低延迟，需本地算力 |
| TTS | OpenAI TTS | 0.5-1s | 音质好，支持流式输出 |
| TTS | Edge TTS | <500ms | 免费，多语言/多音色 |
| Lip-Sync | 音频振幅驱动 | <50ms | 分析 TTS 音频实时驱动下颌骨骼 |
| Lip-Sync | Viseme 映射 | <50ms | 需 TTS 提供音素时间戳，更精准但依赖度高 |

**推荐**：STT 优先使用浏览器 Web Speech API（零延迟、零成本），回退到 Whisper API；TTS 使用 Edge TTS（免费多语言）；Lip-Sync 使用音频振幅驱动方案（与 TTS 解耦，通用性好）。

#### 表情系统

VRM 标准定义了 BlendShape 预设（happy/angry/sad/relaxed/surprised 等），通过 `VRMExpressionManager` 可直接控制：

| 语义场景 | 触发表情 | 表情预设 |
|---------|---------|---------|
| 用户回答正确 | 鼓励/开心 | happy |
| 用户卡顿/出错 | 温和/思考 | relaxed |
| AI 思考回复中 | 专注 | (闭眼+微点头) |
| 对话结束告别 | 挥手/微笑 | happy + 自定义手势 |
| MHI 状态反馈 | 对应情绪 | healthy=happy, attention=surprised, danger=sad |

#### 可参考开源项目

| 项目 | 定位 | 亮点 |
|------|------|------|
| **@pixiv/three-vrm** | VRM 渲染核心库 | Pixiv 官方维护，支持 VRM 0.x/1.0，MToon 着色器，SpringBone 物理 |
| **VRoid Hub** | 免费VRM模型平台 | 数千个免费可商用 VRM 角色，支持条件过滤 |
| **kwea123/ChatGPT-VRM** | VRM + ChatGPT 聊天 | 完整的 Web 端 VRM 对话 Demo，含 lip-sync + 表情 |
| **AI-WTA/Speech-to-VRM** | 语音驱动VRM | 浏览器端 STT → LLM → TTS → VRM 全链路参考实现 |


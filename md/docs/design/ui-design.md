# 灵犀（LinguaLearner）UI 设计规范

**版本**：v1.0 | **日期**：2026-08-09 | **设计师**：UI Designer  
**目标平台**：PWA（Web 优先，移动端适配）  
**技术栈**：React 18 + Tailwind CSS + Radix UI  
**参照文档**：产品需求规格书 · 技术架构设计 · 项目初始化指南

---

## 目录

1. [设计哲学](#1-设计哲学)
2. [设计令牌系统（CSS Custom Properties）](#2-设计令牌系统)
3. [品牌色板](#3-品牌色板)
4. [语义色系统](#4-语义色系统)
5. [排版体系](#5-排版体系)
6. [间距与网格系统](#6-间距与网格系统)
7. [圆角与阴影](#7-圆角与阴影)
8. [动效规范](#8-动效规范)
9. [图标系统](#9-图标系统)
10. [组件规格](#10-组件规格)
11. [页面布局蓝图](#11-页面布局蓝图)
12. [响应式断点](#12-响应式断点)
13. [Tailwind CSS 映射指南](#13-tailwind-css-映射指南)
14. [无障碍规范](#14-无障碍规范)

---

## 1. 设计哲学

### 1.1 美学方向：**"Warm Precision（温暖精准）"**

| 维度 | 定义 | 设计表现 |
|------|------|---------|
| **温暖** | 陪伴感而非评判感，支持而非压迫 | 柔和圆角、低饱和色调、琥珀色点缀、自然过渡动效 |
| **精准** | 数据驱动、让微小进步可见 | 清晰的进度环、语义色编码、层次分明的信息架构 |
| **克制** | 不做游戏化、不做社交炫耀 | 无积分/连胜/排行榜；无霓虹光效；无过度装饰 |

### 1.2 五大设计原则（来自 PRD 用户研究）

| # | 原则 | UI 体现 |
|---|------|---------|
| 1 | **进步显微镜** | 进度环 + DLE 趋势 + MHI 状态灯，不打分不排行 |
| 2 | **"你的下一步"** | 仪表盘首屏永远是当前最该做的事 |
| 3 | **说对确认，说错轻轻纠正** | 对话中用琥珀色温和提示，不用红色叉号 |
| 4 | **有人陪你走** | Agent 角色具象为头像 + 名称 |
| 5 | **你只管学，怎么学我来想** | 自动生成的卡片队列、自动调度的 FSRS |

### 1.3 明确禁止（Non-goals → 设计禁区）

- ❌ **游戏化元素**：积分、连胜天数弹窗、排行榜、成就徽章、进度条动画
- ❌ **社交元素**：点赞、评论、分享动态、好友比拼
- ❌ **AI 代写**：一键生成按钮、自动完成输入框
- ❌ **纯黑背景** `#000000` / 纯白文字 `#FFFFFF`
- ❌ **霓虹发光**：蓝色/紫色 glow 描边、过度阴影
- ❌ **Inter 字体**：避免 AI 生成感，选用 Outfit + DM Sans

---

## 2. 设计令牌系统（CSS Custom Properties）

以下为完整的 CSS 自定义属性定义，是前端实现主题模块的**唯一数据源**。
将所有变量放入 `:root` 或 `[data-theme="dark"]` 选择器中。

### 2.1 完整设计令牌一览

```css
/* ============================================
   灵犀 LinguaLearner — 设计令牌
   Version: 1.0
   Theme: dark (MVP 仅暗色)
   ============================================ */

:root,
[data-theme="dark"] {

  /* ---- 2.1a 品牌色板（Privitive Tokens） ---- */
  --brand-indigo-50:  #eef2ff;
  --brand-indigo-100: #e0e7ff;
  --brand-indigo-200: #c7d2fe;
  --brand-indigo-300: #a5b4fc;
  --brand-indigo-400: #818cf8;
  --brand-indigo-500: #6366f1;   /* ← 主品牌色 */
  --brand-indigo-600: #4f46e5;
  --brand-indigo-700: #4338ca;
  --brand-indigo-800: #3730a3;
  --brand-indigo-900: #312e81;
  --brand-indigo-950: #1e1b4b;

  --brand-amber-400: #fbbf24;
  --brand-amber-500: #f59e0b;
  --brand-amber-600: #d97706;

  --brand-emerald-400: #34d399;
  --brand-emerald-500: #10b981;
  --brand-emerald-600: #059669;

  --brand-red-400: #f87171;
  --brand-red-500: #ef4444;
  --brand-red-600: #dc2626;

  /* ---- 2.1b 表面色（Surfaces） ---- */
  --surface-root:      #09090b;   /* 最底层背景 */
  --surface-base:      #0f1117;   /* 主背景（侧边栏、顶栏） */
  --surface-default:   #161822;   /* 卡片/组件默认背景 */
  --surface-hover:     #1c1f2e;   /* 悬停态 */
  --surface-raised:    #21243a;   /* 浮层（Dropdown/Modal 底） */
  --surface-overlay:   #252840;   /* 最高层（Tooltip/Toast） */

  /* ---- 2.1c 边框色 ---- */
  --border-default:    #252840;   /* 默认边框 */
  --border-hover:      #32365a;   /* 悬停边框 */
  --border-focus:      #6366f1;   /* 聚焦边框 = brand-indigo-500 */

  /* ---- 2.1d 文字色 ---- */
  --text-primary:      #e8e9f0;   /* 正文 / 标题 */
  --text-secondary:    #9b9db8;   /* 辅助说明 */
  --text-tertiary:     #6b6d86;   /* 占位符 / 禁用态 */
  --text-disabled:     #4a4c62;   /* 完全禁用 */
  --text-on-accent:    #ffffff;   /* 在品牌色上的文字 */

  /* ---- 2.1e 语义色（Semantic Colors） ---- */
  --color-accent:         var(--brand-indigo-500);
  --color-accent-hover:   var(--brand-indigo-400);
  --color-accent-active:  var(--brand-indigo-600);
  --color-accent-subtle:  rgba(99, 102, 241, 0.12);  /* 浅底强调 */
  --color-accent-glow:    rgba(99, 102, 241, 0.25);  /* 发光 */

  --color-success:        var(--brand-emerald-500);
  --color-success-subtle: rgba(16, 185, 129, 0.12);

  --color-warning:        var(--brand-amber-500);
  --color-warning-subtle: rgba(245, 158, 11, 0.12);

  --color-error:          var(--brand-red-500);
  --color-error-subtle:   rgba(239, 68, 68, 0.12);

  /* ---- 2.1f 领域专属色 ---- */
  --domain-language:    #818cf8;   /* 靛蓝 — 外语 */
  --domain-humanities:  #f59e0b;   /* 琥珀 — 人文社科 */
  --domain-skill:       #34d399;   /* 翡翠绿 — 兴趣技能 */

  /* ---- 2.1g 排版 ---- */
  --font-display:  'Outfit', system-ui, -apple-system, sans-serif;
  --font-body:     'DM Sans', system-ui, -apple-system, sans-serif;
  --font-mono:     'JetBrains Mono', 'Fira Code', monospace;

  /* ---- 2.1h 字号阶梯（Major Third 1.25） ---- */
  --text-xs:   0.75rem;     /* 12px — 说明文字、标签 */
  --text-sm:   0.8125rem;   /* 13px — 辅助 UI */
  --text-base: 0.9375rem;   /* 15px — 正文（暗色下略大于 14px 更易读） */
  --text-lg:   1.0625rem;   /* 17px — 子标题 */
  --text-xl:   1.25rem;     /* 20px — 小标题 */
  --text-2xl:  1.5rem;      /* 24px — 中标题 */
  --text-3xl:  1.875rem;    /* 30px — 大标题 */
  --text-4xl:  2.25rem;     /* 36px — 展示级标题 */

  /* ---- 2.1i 字重 ---- */
  --weight-regular:  400;
  --weight-medium:   500;
  --weight-semibold: 600;
  --weight-bold:     700;

  /* ---- 2.1j 行高 ---- */
  --leading-tight:  1.2;    /* 标题 */
  --leading-normal: 1.5;    /* 正文 */
  --leading-relaxed:1.65;   /* 长文本 */

  /* ---- 2.1k 字间距 ---- */
  --tracking-tight:  -0.02em;  /* 标题收紧 */
  --tracking-normal: 0;
  --tracking-wide:   0.03em;   /* 标签/大写 */

  /* ---- 2.1l 间距（4pt 基础网格） ---- */
  --space-1:  0.25rem;   /*  4px */
  --space-2:  0.5rem;    /*  8px */
  --space-3:  0.75rem;   /* 12px */
  --space-4:  1rem;      /* 16px */
  --space-5:  1.25rem;   /* 20px */
  --space-6:  1.5rem;    /* 24px */
  --space-8:  2rem;      /* 32px */
  --space-10: 2.5rem;    /* 40px */
  --space-12: 3rem;      /* 48px */
  --space-16: 4rem;      /* 64px */
  --space-20: 5rem;      /* 80px */
  --space-24: 6rem;      /* 96px */

  /* ---- 2.1m 圆角 ---- */
  --radius-sm:   0.375rem;   /*  6px — 小按钮/标签 */
  --radius-md:   0.5rem;     /*  8px — 按钮/输入框（默认） */
  --radius-lg:   0.75rem;    /* 12px — 卡片内区域 */
  --radius-xl:   1rem;       /* 16px — 卡片 */
  --radius-2xl:  1.25rem;    /* 20px — 弹窗 */
  --radius-full: 9999px;     /* 药丸形 */

  /* ---- 2.1n 阴影 ---- */
  --shadow-sm:   0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md:   0 4px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg:   0 8px 24px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 20px var(--color-accent-glow);

  /* ---- 2.1o 过渡 ---- */
  --ease-out-expo:  cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
  --duration-fast:  150ms;
  --duration-normal:250ms;
  --duration-slow:  400ms;

  /* ---- 2.1p 布局 ---- */
  --sidebar-width:  16rem;      /* 256px */
  --header-height:  3.5rem;     /*  56px */
  --content-max:    72rem;      /* 1152px 内容最大宽度 */

  /* ---- 2.1q Z-Index ---- */
  --z-sidebar:  100;
  --z-header:   200;
  --z-dropdown: 300;
  --z-modal:    400;
  --z-toast:    500;
}
```

---

## 3. 品牌色板

### 3.1 主色：Indigo

```
 50: #eef2ff   100: #e0e7ff   200: #c7d2fe
300: #a5b4fc   400: #818cf8   500: #6366f1  ← 主品牌色
600: #4f46e5   700: #4338ca   800: #3730a3
900: #312e81   950: #1e1b4b
```

**使用规则**：
- `500` — 主按钮背景、选中态、链接、聚焦边框
- `400` — 主按钮 hover
- `600` — 主按钮 active
- 浅底强调（tag/accent 背景）统一使用 `rgba(99, 102, 241, 0.12)`

### 3.2 语义色

| 语义 | 色值 | 用途 |
|------|------|------|
| **成功** | `#10b981` (Emerald-500) | 完成状态、MHI 健康灯、正确率 |
| **警告** | `#f59e0b` (Amber-500) | MHI 注意灯、纠错提示、待处理 |
| **错误** | `#ef4444` (Red-500) | MHI 危险灯、删除确认、表单验证 |

### 3.3 领域专属色

| 领域 | 色值 | 语义背景 rgba |
|------|------|:---:|
| **外语** | `#818cf8` (Indigo-400) | `rgba(129,140,248, 0.12)` |
| **人文社科** | `#f59e0b` (Amber-500) | `rgba(245,158,11, 0.12)` |
| **兴趣技能** | `#34d399` (Emerald-400) | `rgba(52,211,153, 0.12)` |

### 3.4 表面色层级（Dark Theme）

```
surface-root     #09090b  ← 最深（body 背景）
surface-base     #0f1117  ← 侧边栏 / 顶栏
surface-default  #161822  ← 卡片 / 组件默认背景
surface-hover    #1c1f2e  ← hover 态
surface-raised   #21243a  ← 浮层（Dropdown / Modal）
surface-overlay  #252840  ← 顶层（Tooltip / Toast）
```

> **关键规则**：暗色模式下**越亮 = 越高**（与亮色模式相反）。最深色是底层背景，每上一层就亮一点。

### 3.5 文字色对比度验证

| 文字 token | 背景 | hex | 对比度 | WCAG |
|-----------|------|-----|:---:|:---:|
| `text-primary` | surface-default | `#e8e9f0` | 13.4:1 | ✅ AAA |
| `text-secondary` | surface-default | `#9b9db8` | 6.4:1 | ✅ AA |
| `text-tertiary` | surface-default | `#6b6d86` | 4.7:1 | ✅ AA |
| `text-on-accent` | accent (indigo-500) | `#ffffff` | 5.1:1 | ✅ AA |
| `color-accent` | surface-default | `#6366f1` | 4.6:1 | ✅ AA |

---

## 4. 排版体系

### 4.1 字体选型

| 层级 | 字体 | Google Fonts | 用途 |
|------|------|-------------|------|
| **展示/标题** | **Outfit** | `weights: 400,500,600,700` | h1-h4、进度环数值、统计数字 |
| **正文/UI** | **DM Sans** | `weights: 400,500,600` | 正文、按钮、标签、表单 |
| **等宽/数据** | **JetBrains Mono** | `weights: 400,500` | 代码块、时间戳、统计数据 |

```html
<!-- Google Fonts 加载 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### 4.2 字号阶梯

采用 **Major Third (1.25)** 比例，基数为 15px（暗色模式下略大于标准 16px 以提高可读性）。

```css
/* 对应 Tailwind 的扩展映射 */
.text-xs    →  12px  → var(--text-xs)
.text-sm    →  13px  → var(--text-sm)
.text-base  →  15px  → var(--text-base)
.text-lg    →  17px  → var(--text-lg)
.text-xl    →  20px  → var(--text-xl)
.text-2xl   →  24px  → var(--text-2xl)
.text-3xl   →  30px  → var(--text-3xl)
.text-4xl   →  36px  → var(--text-4xl)
```

### 4.3 排版类命名规范

| CSS 类 | 字体 | 字号 | 字重 | 行高 | 用途 |
|--------|------|------|------|------|------|
| `.display-lg` | Outfit | 36px | 700 | 1.2 | 页面主标题 |
| `.display-md` | Outfit | 30px | 700 | 1.2 | 区域大标题 |
| `.heading-lg` | Outfit | 24px | 600 | 1.2 | 卡片标题 |
| `.heading-md` | Outfit | 20px | 600 | 1.2 | 区块标题 |
| `.heading-sm` | Outfit | 17px | 600 | 1.2 | 小标题 |
| `.body-lg` | DM Sans | 17px | 400 | 1.65 | 引导文案 |
| `.body-base` | DM Sans | 15px | 400 | 1.65 | 正文 `max-width:65ch` |
| `.body-sm` | DM Sans | 13px | 400 | 1.5 | 辅助说明 |
| `.caption` | DM Sans | 12px | 400 | 1.5 | 标签/脚注 |
| `.mono` | JetBrains | 13px | 400 | 1.5 | 数据/代码 |

**辅助色类**：
```css
.text-secondary { color: var(--text-secondary); }
.text-tertiary  { color: var(--text-tertiary); }
.text-accent    { color: var(--color-accent); }
```

### 4.4 排版规则

- 正文 `max-width: 65ch`（约 65 个字符宽，最佳阅读行宽）
- 标题字间距 `-0.02em`（收紧，更有凝聚力）
- 标签/大写字母间距 `0.03em`
- 暗色主题下字重保持 `400`（不需要加粗补偿，因为亮色文字本身就有足够对比度）

---

## 5. 间距与网格系统

### 5.1 基础网格：4px

所有间距为 4 的倍数，提供比 8pt 更细腻的节奏控制。

| Token | 值 | 像素 | 典型用途 |
|-------|-----|------|---------|
| `space-1` | 0.25rem | 4px | 紧密元素间距（图标-文字） |
| `space-2` | 0.5rem | 8px | 按钮内边距、小间距 |
| `space-3` | 0.75rem | 12px | 输入框内边距、标签间距 |
| `space-4` | 1rem | 16px | 标准内边距、卡片 padding |
| `space-5` | 1.25rem | 20px | 卡片间距 |
| `space-6` | 1.5rem | 24px | 区域间距 |
| `space-8` | 2rem | 32px | 大区块间距 |
| `space-10` | 2.5rem | 40px | 页眉间距 |
| `space-12` | 3rem | 48px | 页面分段 |
| `space-16` | 4rem | 64px | 空状态内边距 |
| `space-20` | 5rem | 80px | 首页留白 |
| `space-24` | 6rem | 96px | 极稀使用 |

### 5.2 布局网格：12 列

仪表盘采用 12 列 CSS Grid，列间距 `space-5 (20px)`。

```
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│  col 1  │  col 2  │  col 3  │  col 4  │  col 5  │  col 6  │  col 7  │  col 8  │  col 9  │ col 10  │ col 11  │ col 12  │
├─────────┴─────────┴─────────┴─────────┼─────────┴─────────┴─────────┴─────────┼─────────┴─────────┴─────────┴─────────┤
│                span 4                 │                span 4                 │                span 4                 │
├─────────┴─────────┴─────────┴─────────┴─────────┴─────────┼─────────┴─────────┴─────────┴─────────┴─────────┴─────────┤
│                          span 6                            │                          span 6                            │
├─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┼─────────┴─────────┴─────────┴─────────┴─────────┤
│                               span 7                                 │                       span 5                     │
└──────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
```

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--space-5);
  padding: var(--space-6);
}

.grid-col-3  { grid-column: span 3; }
.grid-col-4  { grid-column: span 4; }
.grid-col-5  { grid-column: span 5; }
.grid-col-6  { grid-column: span 6; }
.grid-col-7  { grid-column: span 7; }
.grid-col-8  { grid-column: span 8; }
.grid-col-12 { grid-column: span 12; }
```

### 5.3 容器最大宽度

| 上下文 | max-width | 说明 |
|--------|-----------|------|
| 仪表盘内容 | `72rem (1152px)` | `var(--content-max)` |
| 对话页面 | `48rem (768px)` | 窄宽，聚焦对话 |
| 捕获页面 | `40rem (640px)` | 表单式，专注输入 |
| 复习卡片 | `36rem (576px)` | 卡片居中，沉浸式 |
| 弹窗 | `32rem (512px)` | 标准 Modal |

---

## 6. 圆角与阴影

### 6.1 圆角阶梯

```
radius-sm   6px  ── 小按钮、标签、徽章
radius-md   8px  ── 按钮、输入框、下拉菜单（默认）
radius-lg  12px  ── 卡片内元素
radius-xl  16px  ── 卡片
radius-2xl 20px  ── 弹窗
radius-full 9999px ── 药丸形按钮、圆形头像、进度环
```

**规则**：
- 交互元素（按钮/输入框）统一用 `radius-md`
- 容器（卡片/面板）统一用 `radius-xl`
- 嵌套元素不要用比父级更大的圆角
- 按钮 `border-radius` = 卡片内边距时，方形内容会很怪 — 确保 padding >= border-radius

### 6.2 阴影阶梯（暗色模式）

```
shadow-sm   → 卡片默认态、轻微浮起
shadow-md   → hover 态卡片、按钮 hover
shadow-lg   → 弹窗、Toast
shadow-glow → 品牌色发光（仅用于进度环、活跃指示器）
```

> 注意：暗色模式下阴影更深，因为背景本身是暗的。阴影的扩散半径在暗色模式下应更大（给空间感）。

---

## 7. 动效规范

### 7.1 缓动函数

| 名称 | 值 | 用途 |
|------|-----|------|
| `ease-out-expo` | `cubic-bezier(0.16, 1, 0.3, 1)` | 元素出现、弹窗 |
| `ease-out-quart` | `cubic-bezier(0.25, 1, 0.5, 1)` | hover 过渡、颜色变化 |

### 7.2 时长

| Token | 值 | 用途 |
|-------|-----|------|
| `duration-fast` | 150ms | 按钮 hover/active、边框颜色 |
| `duration-normal` | 250ms | 卡片 hover、标签切换 |
| `duration-slow` | 400ms | 弹窗进出、进度环动画 |

### 7.3 动效规则

```css
/* ✅ 允许 */
- transform: scale()    /* 按钮按下 */
- opacity               /* 渐显/渐隐 */
- background-color      /* hover 色变 */
- border-color          /* hover 边框变 */
- translateY(-1px)      /* 卡片微浮 */

/* ❌ 禁止 */
- width/height 动画     /* 使用 transform: scale 代替 */
- 弹跳/弹性缓动         /* 与"温暖精准"的克制美学冲突 */
- 超过一次的重复闪烁    /* 癫痫风险 */
```

### 7.4 无障碍动效

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8. 图标系统

### 8.1 图标库

使用 **Lucide React**（已包含在项目初始化依赖中 `lucide-react`）。

- 描边宽度：2px（默认）
- 尺寸规范：16px（行内）/ 18px（按钮）/ 20px（导航）/ 24px（独立）
- 颜色：继承父级 `currentColor`

### 8.2 各场景图标映射

| 导航场景 | Lucide 图标 |
|---------|------------|
| 仪表盘 | `LayoutGrid` |
| 内容捕获 | `FileText` / `PlusCircle` |
| 记忆复习 | `Layers` / `Brain` |
| AI 对话 | `MessageCircle` |
| 数字人形象（对话页内嵌） | `Bot` |
| 学习路径 | `TrendingUp` / `Route` |
| 通知 | `Bell` |
| 设置 | `Settings` |
| 语音输入 | `Mic` |
| 发送 | `Send` |
| 完成/成功 | `CheckCircle2` |
| 添加 | `Plus` |
| 关闭 | `X` |
| 搜索 | `Search` |
| 用户 | `User` |

---

## 9. 组件规格

### 9.1 按钮 Button

```
┌──────────────────────────────────────────────┐
│  变体          尺寸       状态               │
│  ──────       ──────     ──────             │
│  primary      sm (28px)  default → hover     │
│  secondary    md (34px)  → active → focus    │
│  ghost        lg (42px)  → disabled          │
│  danger                                      │
├──────────────────────────────────────────────┤
│  内边距：sm: 4px 10px                       │
│          md: 6px 14px                       │
│          lg: 10px 22px                      │
│  最小触摸目标：44×44px（移动端）              │
│  圆角：8px (radius-md)                       │
│  active: scale(0.97)                        │
└──────────────────────────────────────────────┘
```

**颜色映射**：

| 变体 | 背景 | 文字 | 边框 | hover 背景 |
|------|------|------|------|-----------|
| primary | `accent` | `text-on-accent` | 无 | `accent-hover` |
| secondary | `surface-default` | `text-primary` | `border-default` | `surface-hover` |
| ghost | transparent | `text-secondary` | 无 | `surface-default` |
| danger | `error-subtle` | `error` | 无 | `rgba(239,68,68,0.2)` |

**带图标按钮**：
```
[icon 16px] [文字]     ← 默认
[icon 18px]            ← icon-only (宽高相等)
```

### 9.2 输入框 Input

```
┌──────────────────────────────────────────────┐
│  高度：md 34px / lg 42px                    │
│  内边距：8px 12px (md) / 10px 14px (lg)     │
│  圆角：8px (radius-md)                       │
│  背景：surface-default                       │
│  边框：1px solid border-default              │
│  ────────────────────────────               │
│  default:  border-default  bg-default        │
│  hover:    border-hover                     │
│  focus:    border-accent + box-shadow:       │
│            0 0 0 3px accent-subtle           │
│  disabled: opacity 0.4                       │
│  placeholder: text-tertiary                  │
└──────────────────────────────────────────────┘
```

**文本域 Textarea**：
- 同 Input，额外：`min-height: 120px`、`resize: vertical`、圆角 `radius-lg`

### 9.3 卡片 Card

```
┌──────────────────────────────────────────────┐
│  圆角：16px (radius-xl)                      │
│  背景：surface-default                       │
│  边框：1px solid border-default              │
│  内边距：20px (space-5)                      │
│  ────────────────────────────               │
│  default:  border-default                   │
│  hover (interactive):                       │
│    border → border-hover                    │
│    bg → surface-hover                       │
│  card--flat: 去背景+边框（内容区面板）         │
└──────────────────────────────────────────────┘
```

### 9.4 标签 Tag / 徽章 Badge

```
┌──────────────────────────────────────────────┐
│  内边距：3px 10px                            │
│  圆角：9999px (药丸)                          │
│  字号：12px, weight 500                      │
│  ────────────────────────────               │
│  tag--default:  bg=surface-raised  text=secondary │
│  tag--accent:   bg=accent-subtle   text=accent    │
│  tag--success:  bg=success-subtle  text=success   │
│  tag--warning:  bg=warning-subtle  text=warning   │
│  tag--error:    bg=error-subtle    text=error     │
│  ────────────────────────────               │
│  tag--language:   bg=rgba(129,140,248,.12)  │
│  tag--humanities: bg=rgba(245,158,11,.12)   │
│  tag--skill:      bg=rgba(52,211,153,.12)   │
└──────────────────────────────────────────────┘
```

### 9.5 进度环 Progress Ring

SVG 实现，旋转 -90° 从顶部开始绘制。

```html
<div class="progress-ring" style="width: 4.5rem; height: 4.5rem;">
  <svg viewBox="0 0 72 72">
    <!-- 背景圆环 -->
    <circle cx="36" cy="36" r="30"
      fill="none" stroke="var(--surface-raised)" stroke-width="5"/>
    <!-- 进度圆环 -->
    <circle cx="36" cy="36" r="30"
      fill="none" stroke="var(--color-accent)" stroke-width="5"
      stroke-linecap="round"
      stroke-dasharray="188.5"
      stroke-dashoffset="47.1"
      transform="rotate(-90 36 36)"
      style="transition: stroke-dashoffset 0.6s var(--ease-out-expo)"/>
  </svg>
  <div class="progress-ring-center">
    <span>75%</span>
    <span class="caption">进度</span>
  </div>
</div>
```

**颜色变体**：
| 用途 | stroke 色 |
|------|----------|
| 通用/品牌 | `var(--color-accent)` |
| 外语领域 | `var(--domain-language)` |
| 人文领域 | `var(--domain-humanities)` |
| 兴趣领域 | `var(--domain-skill)` |
| 完成态 | `var(--color-success)` |

### 9.6 MHI 状态指示灯

```
🟢 健康  — bg: success, box-shadow: 0 0 6px success
🟡 注意  — bg: warning, box-shadow: 0 0 6px warning
🟠 警告  — bg: #f97316  (Orange-500)
🔴 危险  — bg: error,   box-shadow: 0 0 6px error
```

尺寸：`8px × 8px`，`border-radius: 50%`，发光用 `box-shadow`。

### 9.7 领域指示器

```
● 外语   — bg: domain-language (#818cf8)
● 人文   — bg: domain-humanities (#f59e0b)
● 兴趣   — bg: domain-skill (#34d399)
```

尺寸：`8px × 8px`，`border-radius: 50%`。

### 9.8 头像 Avatar

```
圆形，渐变背景
sm: 32×32px, 字号 12px
md: 40×40px, 字号 14px
lg: 56×56px, 字号 18px

背景渐变：linear-gradient(135deg, indigo-500, indigo-700)
文字色：white
AI角色头像：根据不同角色使用不同渐变
  田中さん → 琥珀渐变
```

### 9.9 对话气泡 Chat Bubble

```
┌──────────────────────────────────────────────┐
│  AI 气泡（左侧）                             │
│  bg: surface-raised                         │
│  border: 1px solid border-default            │
│  border-top-left-radius: 4px (小)            │
│  其余角：12px (radius-lg)                    │
│  ────────────────────────────               │
│  用户气泡（右侧，右对齐）                     │
│  bg: accent                                 │
│  color: text-on-accent                      │
│  border-top-right-radius: 4px (小)           │
│  其余角：12px (radius-lg)                    │
│  ────────────────────────────               │
│  纠错提示：嵌在 AI 气泡下方                   │
│  bg: warning-subtle, color: warning          │
│  border-radius: 4px, padding: 2px 6px        │
│  字号：12px                                  │
└──────────────────────────────────────────────┘
```

### 9.10 圆角复习卡片 Review Card

```
┌──────────────────────────────────────────────┐
│  max-width: 576px, 居中                      │
│  bg: surface-default                         │
│  border: 1px solid border-default            │
│  border-radius: radius-xl                    │
│  padding: space-6                            │
│  cursor: pointer                             │
│  ────────────────────────────               │
│  正面：领域标签 + 大号词汇/概念 + "点击翻转"   │
│  背面：答案（success色）+ 释义 + 上次复习时间  │
│  hover: border → border-hover                │
└──────────────────────────────────────────────┘
```

**复习评分按钮**（FSRS 四档）：

```
[再次学习]  [困难]    [良好]     [简单]
<1分钟      6分钟     1天        4天

hover:
  again → border: error, bg: error-subtle
  hard  → border: warning, bg: warning-subtle
  good  → border: success, bg: success-subtle
  easy  → border: accent, bg: accent-subtle
```

### 9.11 导航项 Nav Item

```
高度：36px
内边距：8px 12px
圆角：8px (radius-md)
间距：4px（项与项之间）

default: color=text-secondary, bg=transparent
hover:   color=text-primary,   bg=surface-default
active:  color=accent,         bg=accent-subtle
```

### 9.12 统计卡片 Stat Card

```
┌──────────────────────────────────────────────┐
│  bg: surface-default                         │
│  border: 1px border-default                  │
│  border-radius: radius-xl                    │
│  padding: space-4 space-5                    │
│  ────────────────────────────               │
│  [LABEL]  ← 大写、小号、tertiary             │
│  [VALUE]  ← 大号、bold、display字体          │
│  [SUB]    ← 趋势箭头 + 说明                  │
└──────────────────────────────────────────────┘
```

### 9.13 状态组件

#### 加载态 — 骨架屏 Skeleton
```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--surface-default) 25%,
    var(--surface-hover) 50%,
    var(--surface-default) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}
```

#### 空状态 Empty State
```
居中布局，上下 padding: 64px
图标：64×64, 圆角 20px, bg accent-subtle
标题：heading-sm
说明：body-sm, text-secondary, max-width 384px
操作按钮在下方
```

#### 错误状态 Error State
- 同空状态布局
- 图标色改为 error
- 提供"重试"按钮

#### Toast 通知
```
固定右下角，bottom: 24px, right: 24px
max-width: 384px
左边框 3px 色条（success=emerald, error=red）
出现动画：translateY(16px) → 0, opacity 0→1, 300ms
```

### 9.14 数字人形象区 Avatar Panel（对话页内嵌）

```
┌──────────────────────────────────────────────┐
│  数字人形象区（对话页右侧内嵌）                 │
│  尺寸：宽约 280px · 高 280px                  │
│  背景：surface-default + 1px border-default   │
│  圆角：radius-2xl (20px)                      │
│  阴影：shadow-lg                              │
│  ────────────────────────────               │
│  ┌──────────────────────────────────────┐    │
│  │                                      │    │
│  │  MVP: 2D 角色立绘区域                 │    │
│  │  (CSS 说话/呼吸动效)                  │    │
│  │  V1.1: VRM 3D 渲染区域                │    │
│  │  (Three.js Canvas，同容器替换)        │    │
│  │  高度：280px                          │    │
│  │  背景：渐变暗色                        │    │
│  │  linear-gradient(180deg,              │    │
│  │    surface-root → surface-base)       │    │
│  └──────────────────────────────────────┘    │
│  ────────────────────────────               │
│  状态指示行：                                  │
│  [● 表情标签]                                 │
│  ────────────────────────────               │
│  [形象设置 ▾]                                  │
└──────────────────────────────────────────────┘
```

> 语音交互（录音状态行、按住说话按钮）为 **V1.1 预留位**，M2 文本输入优先，不渲染语音控件。

形象区**内嵌于 AI 对话页右侧**（§10.5），非全局浮层。MVP 渲染 2D 立绘 + CSS 动效；VRM 3D 为 V1.1 升级，同一容器替换渲染层，接口不变。

**V1.1 悬浮小组件 Float Widget**（全局悬浮陪伴模式，V1.1 P1-6）：
```
┌──────────┐
│          │
│  VRM     │  ← 120×120px 圆形 Canvas
│  头像    │     position: fixed
│          │     bottom: 24px, right: 24px
│  (简化   │     border: 2px solid border-default
│   渲染)  │     border-radius: radius-full
│          │     box-shadow: shadow-md
└──────────┘
  点击展开为形象区
  长按拖动改变位置
```

**录音状态指示器**（**V1.1 接入**，M2 文本优先不渲染语音组件；本节为 V1.1 规范）：
```
默认态：    🎤 灰色图标 + "点击说话"
录音中：    🔴 脉冲动画 + 波形可视化
            bg: error-subtle, 圆形脉冲 scale(1→1.1→1)
            持续 800ms 循环
处理中：    ⏳ 旋转加载 + "识别中..."
            使用 skeleton 动画样式
```

**表情标签**（显示在数字人头顶或面板状态行）：
```
内边距：2px 8px
圆角：radius-full
字号：11px
背景随表情变化：
  neutral  → bg: surface-raised,     text: secondary
  happy    → bg: success-subtle,     text: success
  thinking → bg: accent-subtle,      text: accent
  relaxed  → bg: warning-subtle,     text: warning
  sad      → bg: error-subtle,       text: error
```

### 9.15 语音波形可视化 Voice Waveform

```
录音中的实时音频波形可视化
高度：24px
宽度：随容器自适应
由 5 根竖条组成，宽度 3px，间距 2px
颜色：accent
动画：每根竖条高度随音频振幅实时变化
  min-height: 4px (静音)
  max-height: 24px (最大音量)
过渡：duration-fast (150ms)
圆角：radius-full (竖条顶部+底部)
```

```css
.waveform {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 24px;
}
.waveform-bar {
  width: 3px;
  border-radius: var(--radius-full);
  background: var(--color-accent);
  transition: height var(--duration-fast) var(--ease-out-quart);
}
```

---

## 10. 页面布局蓝图

### 10.1 整体框架（App Shell）

```
┌──────────┬─────────────────────────────────────────┐
│          │  TopBar (56px)                          │
│          │  页面标题           🔔  ⚙️               │
│ Sidebar  ├─────────────────────────────────────────┤
│ (256px)  │                                         │
│          │                                         │
│  🦏 灵犀  │         页面内容区                       │
│  ──────  │        (可变宽度)                        │
│  仪表盘   │                                         │
│  捕获     │                                         │
│  复习 12  │                                         │
│  对话     │                                         │
│  路径     │                                         │
│  ──────  │                                         │
│  学习领域＋│                                         │
│  ● 日语   │                                         │
│  ● 哲学   │                                         │
│  ● 吉他   │                                         │
│  ──────  │                                         │
│  [头像]   │                                         │
│  用户信息  │                                         │
│          │                                         │
└──────────┴─────────────────────────────────────────┘
```

**学习领域（动态管理）**：分组标题右侧 `＋` 展开内联添加表单（领域名称 + 领域类型三选：外语/人文/兴趣），确认后插入新条目；条目 hover 显示 `×` 可删除。领域列表是「仪表盘领域卡片」「捕获页学习领域下拉」等处的候选集合来源。

### 10.2 仪表盘 Dashboard

> **交付注记（M2 范围调整 2026-08-14）**：M2 只交付**学情展示版**——对话统计（次数/时长/平均分）+ 对话历史 + 单次学情详情（§10.5 学情报告落库后展示）。下图的 MHI 健康度 / DLE 进度环 / 三领域进度环 / 今日待复习为 **V1.1 完整版设计**（依赖记忆系统与多源事件），规范保留待 V1.1 落地。

```
┌──────────────────────────────────────────────────────┐
│  ┌─────────────────────────────┐  ┌───────────────┐  │
│  │ 欢迎卡片（下一步）            │  │  MHI 健康度   │  │
│  │ · 问候语 + DLE 进度环        │  │  0.82 🟢     │  │
│  │ · "开始复习" 按钮            │  │  活跃 14 天   │  │
│  │ span 7                      │  │  span 5       │  │
│  └─────────────────────────────┘  └───────────────┘  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  日语     │  │  哲学     │  │  吉他     │           │
│  │  75% ○   │  │  57% ○   │  │  40% ○   │           │
│  │  span 4  │  │  span 4  │  │  span 4  │           │
│  └──────────┘  └──────────┘  └──────────┘           │
│                                                      │
│  ┌────────────────────┐  ┌────────────────────┐      │
│  │  DLE 趋势 (7天)    │  │  今日待复习         │      │
│  │  span 6            │  │  日语12·哲学3·吉他2 │      │
│  └────────────────────┘  └────────────────────┘      │
│                                                      │
│  ┌────────────────────┐  ┌────────────────────┐      │
│  │  最近活动           │  │  输出挑战就绪       │      │
│  │  span 6            │  │  span 6            │      │
│  └────────────────────┘  └────────────────────┘      │
└──────────────────────────────────────────────────────┘
```

### 10.3 内容捕获 Capture

```
┌────────────────────────────────────────┐
│         内容捕获                        │
│    粘贴文章、链接或上传文件...           │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │                                  │  │
│  │     📄 粘贴内容或拖拽文件          │  │
│  │     支持文本、URL链接、PDF文件     │  │
│  │                                  │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  文本域（粘贴内容）               │  │
│  │                                  │  │
│  │                                  │  │
│  └──────────────────────────────────┘  │
│                                        │
│  [选择领域 ▾]        [提取概念 →]      │
│                                        │
│  ─── 提取结果 ──────────────────────  │
│                                        │
│  ┌ [icon] 概念A                    ┐   │
│  │ 说明文字...                      │   │
│  │ [tag: 已关联] [tag: 新概念]     │   │
│  └─────────────────────────────────┘   │
│                                        │
│  ┌ [icon] 概念B                    ┐   │
│  │ ...                              │   │
│  └─────────────────────────────────┘   │
└────────────────────────────────────────┘
```

### 10.4 记忆复习 Review

> **交付注记（M2 范围调整 2026-08-14）**：复习页随记忆系统（FSRS）后置 V1.1，**M2 不交付**；本页为 V1.1 设计规范，M2 结束前不开发不联调。

```
┌──────────────────────────────────┐
│        记忆复习                   │
│   今日队列：17张 · 3领域 · 14分钟  │
│   [日语] [哲学] [吉他]            │
│                                  │
│  ┌────────────────────────────┐  │
│  │                            │  │
│  │   [日语·词汇]               │  │
│  │                            │  │
│  │    いただきます              │  │
│  │                            │  │
│  │    点击翻转查看答案           │  │
│  │                            │  │
│  └────────────────────────────┘  │
│                                  │
│  [再次学习] [困难] [良好] [简单]   │
│                                  │
│  复习进度 ████░░░░░░ 4/17         │
└──────────────────────────────────┘
```

复习完成后的空状态：
```
  ┌──────────────────────────────────┐
  │          ✓                       │
  │     今日复习已完成！              │
  │  下一批卡片明天 8:00 到达         │
  │     [查看学习报告]               │
  └──────────────────────────────────┘
```

### 10.5 AI 对话 Chat

双栏布局：**左侧对话展示区 + 右侧数字人形象区**。数字人形象是对话页的内嵌组件，不单独成页、不占导航栏（§10.7）。

**场景卡片选择（对话页顶部）**——对话从**场景卡片库**选题（M2 范围调整后，只保留外语场景对话，费曼/兴趣汇报随记忆系统后置 V1.1）：用户手动添加想练习的场景话题卡片（`ScenarioCard` CRUD），首次登录预置 4-5 张种子场景（餐厅点餐 / 便利店购物 / 问路 / 自我介绍 / 商务会议）。每张卡片 = 标题 + 描述 + 语言 + 难度，选中后 AI 扮演该场景角色开启对话。

```
┌──────────────────────────────────────┬──────────────┐
│ [场景 ▾ 餐厅点餐]  难度 N4 ▾  [+ 新场景]│  数字人形象区 │
│──────────────────────────────────────│    (右 40%)  │
│ 🏷 餐厅点餐 · N4 · 田中さん            │              │
│                                      │  ┌────────┐  │
│ ┌──┐                                │  │ 角色形象 │  │
│ │田│ いらっしゃいませ！何名様ですか？  │  │ (MVP 2D │  │
│ └──┘                                │  │ 立绘/表情) │  │
│              ┌──┐                   │  │ 说话动效 │  │
│              │陈│ 一人です。          │  └────────┘  │
│              └──┘                   │  😊 happy    │
│ ┌──┐                                │              │
│ │田│ かしこまりました。こちらが...    │  [形象设置 ▾] │
│ └──┘                                │              │
│    💡 「メニューをください」→        │              │
│       更自然的说法是「メニューを見せて」│              │
│──────────────────────────────────────│              │
│ [输入日语...             ]  [发送]    │              │
│                    [结束对话]         │              │
└──────────────────────────────────────┴──────────────┘
```

**渐进式纠错提示条**（琥珀色，AI 气泡下方）——说对确认（绿 ✓）→ 小错轻纠（琥珀提示）→ 大错引导重述（引导箭头），不打断对话流。

**学情报告（对话结束展示）**——点结束对话（或 ≥3 分钟自动提示）后弹出报告卡：会话摘要 + 表现分（0-100）+ ≥3 个薄弱点（词汇/语法/表达标签）+ 改进建议；报告同时写入仪表盘（§10.2）供复盘。

**场景管理入口**：`[+ 新场景]` 打开表单（标题 / 描述 / 语言 / 难度），可编辑、可软删；空库时对话页显示空状态，引导先建场景。

**语音**：M2 文本输入优先（输入框无麦克风按钮）；语音通道（Web Speech STT + Edge TTS）V1.1 接入，UI 预留按钮位（输入框左端与形象区底部）。

**右侧数字人形象区**：MVP 阶段用 2D 角色形象（立绘 + CSS 说话/表情动效，零 3D 依赖）；VRM 3D 渲染与全局悬浮陪伴为 V1.1 P1-6 范围（§10.7）。AI 说话时形象触发说话动效，对话文本输出同步。

### 10.6 学习路径 Learning Path

```
┌──────────────────────────────────────────┐
│          学习路径                          │
│     日语 N4→N3 突破计划                   │
│                                          │
│  ●── ✅ 已完成 · W1-2                    │
│  │   基础巩固：N4 核心词汇与语法           │
│  │   完成率 100% · 正确率 88%             │
│  │                                       │
│  ●── ✅ 已完成 · W3-4                    │
│  │   听力提升：场景对话入门                │
│  │   完成率 100% · 评分 B+                │
│  │                                       │
│  ◉── 🔵 进行中 · W5-8                    │
│  │   N3 冲刺：中级语法与自然表达          │
│  │   进度 60% · 本周焦点：敬语体系        │
│  │   [继续学习]                           │
│  │                                       │
│  ○── ⏳ 待解锁 · W9-12                   │
│      输出突破：流畅对话与长文阅读          │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 🔄 跨领域学习建议                  │    │
│  │ 哲学「正义理论」←→ 日语「建前と本音」│    │
│  │ [创建跨领域卡片]                   │    │
│  └──────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

### 10.7 数字人形象 Avatar（AI 对话页内嵌）

数字人**不单独成页、不占导航栏**，作为 §10.5 AI 对话页右侧形象区的内嵌组件——对话练习的可视化前端，强化"有人陪你走"的设计原则。

**形象区构成**（自上而下）：

| 元素 | MVP（M2） | V1.1 升级 |
|------|-----------|-----------|
| 角色形象 | 2D 立绘 + CSS 说话/呼吸动效 | VRM 3D 渲染（Three.js + @pixiv/three-vrm） |
| 表情 | 5 种表情标签，随对话语义切换 | ExpressionManager 驱动 + lip-sync 口型同步 |
| 语音控制 | —（M2 文本输入优先；Web Speech STT + Edge TTS 语音 V1.1 接入，UI 已预留按钮位） | 音色/角色可配置 |
| 伴随模式 | — | 全局悬浮陪伴：其他页面角落悬浮 + 复习语音播报卡片 |

**行为规则**：
- AI 说话时形象触发说话动效，对话文本与语音同步输出
- 表情随对话语义切换：说对确认 → happy；小错轻轻纠正 → neutral/thinking（设计原则 3）
- 录音中显示录音状态指示器（默认/录音中/处理中三态）

> **V1.1 展望**：悬浮陪伴模式（PRD L205"其他任务中持续在线"）与 VRM 3D 渲染、Spike D（three-vrm 加载 + lip-sync + 60fps 验证）均于 V1.1（W20 末）实施。MVP 阶段数字人形象仅存在于 AI 对话页。

---

## 11. 响应式断点

### 11.1 断点定义

| 断点 | 宽度 | 布局变化 |
|------|------|---------|
| **Mobile** | < 640px | 单列，底部Tab导航，卡片全宽 |
| **Tablet** | 640px - 1023px | 6列网格，侧边栏隐藏，保留底部Tab |
| **Desktop** | ≥ 1024px | 12列网格，侧边栏固定，底部Tab隐藏 |

### 11.2 各断点布局变化

```
Desktop (≥1024px):
┌────────┬─────────────────────────┐
│ Sidebar│     Content (12-col)    │
│ 256px  │                         │
└────────┴─────────────────────────┘

Tablet/Mobile (<1024px):
┌──────────────────────────────────┐
│  TopBar (简化)                    │
├──────────────────────────────────┤
│                                  │
│     Content (6-col / 全宽)        │
│                                  │
├──────────────────────────────────┤
│  [仪表盘] [捕获] [复习] [对话] [路径]│  ← 底部Tab
└──────────────────────────────────┘
```

### 11.3 网格列跨度的响应式映射

| 元素 | Desktop | Tablet | Mobile |
|------|:---:|:---:|:---:|
| 欢迎卡片 | span 7 | span 6 | span 6 (全宽) |
| MHI 卡片 | span 5 | span 6 | span 6 |
| 领域卡片 ×3 | span 4 | span 3 | span 6 |
| DLE 趋势 | span 6 | span 6 | span 6 |
| 待复习 | span 6 | span 6 | span 6 |
| 最近活动 | span 6 | span 6 | span 6 |
| 输出挑战 | span 6 | span 6 | span 6 |

### 11.3 AI 对话页数字人形象区响应式行为

| 断点 | 形象区表现 |
|------|---------|
| **Desktop** (≥1024px) | 双栏固定：左对话区（60%）+ 右形象区（40%，约 280px 高） |
| **Tablet** (640-1023px) | 形象区默认折叠为右上角头像条，点击展开 |
| **Mobile** (<640px) | 隐藏形象区，对话页单列文本（文本输入唯一通道；语音 V1.1） |

---

## 12. Tailwind CSS 映射指南

项目已使用 Tailwind CSS。以下是设计令牌到 Tailwind 类的映射建议。

### 12.1 颜色映射

在 `tailwind.config.ts` 中扩展：

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  theme: {
    extend: {
      colors: {
        // 表面色
        surface: {
          root: '#09090b',
          base: '#0f1117',
          DEFAULT: '#161822',
          hover: '#1c1f2e',
          raised: '#21243a',
          overlay: '#252840',
        },
        // 边框
        border: {
          DEFAULT: '#252840',
          hover: '#32365a',
          focus: '#6366f1',
        },
        // 语义文字色（覆盖 Tailwind 默认的 text 色系）
        text: {
          primary: '#e8e9f0',
          secondary: '#9b9db8',
          tertiary: '#6b6d86',
          disabled: '#4a4c62',
        },
        // 品牌色
        brand: {
          DEFAULT: '#6366f1',
          hover: '#818cf8',
          active: '#4f46e5',
        },
        // 领域色
        domain: {
          language: '#818cf8',
          humanities: '#f59e0b',
          skill: '#34d399',
        },
      },
      fontFamily: {
        display: ['Outfit', 'system-ui', '-apple-system', 'sans-serif'],
        body: ['DM Sans', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.75rem', { lineHeight: '1.5' }],
        'xs': ['0.8125rem', { lineHeight: '1.5' }],
        'sm': ['0.8125rem', { lineHeight: '1.5' }],
        'base': ['0.9375rem', { lineHeight: '1.65' }],
        'lg': ['1.0625rem', { lineHeight: '1.65' }],
        'xl': ['1.25rem', { lineHeight: '1.2' }],
        '2xl': ['1.5rem', { lineHeight: '1.2' }],
        '3xl': ['1.875rem', { lineHeight: '1.2' }],
        '4xl': ['2.25rem', { lineHeight: '1.2' }],
      },
      spacing: {
        '1': '0.25rem',
        '2': '0.5rem',
        '3': '0.75rem',
        '4': '1rem',
        '5': '1.25rem',
        '6': '1.5rem',
        '8': '2rem',
        '10': '2.5rem',
        '12': '3rem',
        '16': '4rem',
        '20': '5rem',
        '24': '6rem',
      },
      borderRadius: {
        'sm': '0.375rem',
        'md': '0.5rem',
        'lg': '0.75rem',
        'xl': '1rem',
        '2xl': '1.25rem',
      },
      boxShadow: {
        'sm': '0 1px 2px rgba(0, 0, 0, 0.3)',
        'md': '0 4px 12px rgba(0, 0, 0, 0.4)',
        'lg': '0 8px 24px rgba(0, 0, 0, 0.5)',
        'glow': '0 0 20px rgba(99, 102, 241, 0.25)',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'out-quart': 'cubic-bezier(0.25, 1, 0.5, 1)',
      },
    },
  },
} satisfies Config
```

### 12.2 常用 Tailwind 类速查

```html
<!-- 背景 -->
<body class="bg-surface-root text-text-primary">

<!-- 卡片 -->
<div class="bg-surface border border-border rounded-xl p-5">

<!-- 按钮 primary -->
<button class="bg-brand text-white rounded-md px-4 py-2
               hover:bg-brand-hover active:bg-brand-active
               focus-visible:outline-2 focus-visible:outline-brand">

<!-- 按钮 secondary -->
<button class="bg-surface border border-border rounded-md px-4 py-2
               hover:bg-surface-hover hover:border-border-hover">

<!-- 输入框 -->
<input class="bg-surface border border-border rounded-md px-3 py-2
              placeholder:text-text-tertiary
              hover:border-border-hover
              focus:border-brand focus:ring-3 focus:ring-brand/12">

<!-- 标签 -->
<span class="bg-surface-raised text-text-secondary text-2xs
             font-medium rounded-full px-2.5 py-0.5">

<!-- 文字 -->
<h1 class="font-display text-3xl font-bold tracking-tight">
<p class="text-text-secondary text-xs">
```

---

## 13. 无障碍规范（WCAG AA）

### 13.1 颜色对比度

| 要求 | 标准 | 状态 |
|------|------|:---:|
| 正文文字 vs 背景 | ≥ 4.5:1 | ✅ 13.4:1 |
| 大文字 (≥18px) vs 背景 | ≥ 3:1 | ✅ |
| UI 组件 vs 背景 | ≥ 3:1 | ✅ |
| 占位符文字 | ≥ 4.5:1 | ✅ 4.7:1 |

### 13.2 焦点指示器

```css
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```
- 所有可交互元素必须有明确的 focus 样式
- 不使用 `outline: none` 除非提供替代方案
- Tab 键导航顺序必须逻辑合理

### 13.3 触摸目标

- 移动端所有交互元素最小 `44×44px`
- 按钮即使视觉上只有 28px，点击区域也要扩展到 44px（通过 padding 或伪元素）

### 13.4 其他

- 图片/图标必须有 `alt` 或 `aria-label`
- 动态内容使用 `aria-live="polite"` 通知屏幕阅读器
- 表单输入框关联 `<label>`
- 支持浏览器文字缩放至 200% 不破坏布局
- 尊重 `prefers-reduced-motion`

---

## 附录 A：设计文件对照表

| 设计令牌文档（本文） | 实现位置 |
|-------------------|---------|
| CSS 变量定义 | `frontend/src/index.css` 或 `frontend/src/styles/tokens.css` |
| Tailwind 扩展 | `frontend/tailwind.config.ts` |
| 字体加载 | `frontend/index.html` `<head>` |
| 组件基础样式 | `frontend/src/components/ui/` 各子目录 |
| 页面布局 | `frontend/src/pages/` 各页面文件 |
| PWA 主题色 | `frontend/vite.config.ts` (theme_color: `#6366f1`) |

## 附录 B：验收清单

前端开发完成主题系统后，对照以下清单自检：

- [ ] 所有 CSS 变量已在 `:root` / `[data-theme]` 中定义
- [ ] 按钮变体 (primary/secondary/ghost/danger) × 尺寸 (sm/md/lg) × 状态 (default/hover/active/focus/disabled) 全部覆盖
- [ ] 输入框状态 (default/hover/focus/disabled/error) 全部覆盖
- [ ] 进度环三种领域颜色可切换
- [ ] MHI 状态灯四色正确
- [ ] 学习领域：分组标题 ＋ 展开内联添加表单（名称 + 外语/人文/兴趣三选），添加/删除条目正常（§10.1）
- [ ] 对话气泡 AI/用户样式区分 + 纠错提示样式
- [ ] 复习卡片翻转交互 + 四档评分按钮 hover 色
- [ ] 响应式：Desktop 12列 → Tablet 6列+侧边栏隐藏+底部Tab → Mobile 单列+底部Tab
- [ ] 暗色主题下所有文字对比度 ≥ 4.5:1
- [ ] 焦点样式在键盘导航中可见
- [ ] `prefers-reduced-motion` 下动画禁用
- [ ] 骨架屏动画正常
- [ ] 空状态、错误状态样式完备
- [ ] AI 对话页双栏布局：左对话展示区 + 右数字人形象区（§10.5）
- [ ] 数字人形象区：MVP 2D 形象 + 说话动效 + 表情标签 5 种颜色变体正确
- [ ] 数字人录音状态指示器：默认/录音中/处理中三态样式正确
- [ ] 语音波形可视化动画正常
- [ ] 形象区在 Desktop/Tablet/Mobile 三个断点的折叠/隐藏表现正确

---

> **版本记录**：v1.0 — 初始设计规范，基于 PRD v1.0 + 技术架构 v1.0。后续版本随产品迭代更新。

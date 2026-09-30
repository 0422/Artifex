// 2026-09-29 产品名此前在多个页面与构建配置中硬编码（登录页标题、侧边栏品牌、
// 引导页/捕获页文案、PWA manifest），改名时需逐处修改且容易遗漏。
// 集中到本文件作为唯一来源，今后更名只改这一个常量。
// 例外：frontend/index.html 的 <title> 是纯静态 HTML、无法 import 变量，
// 改名时需额外手工同步那一处。
export const PRODUCT_NAME = 'Artifex'

// 2026-09-30 新增边缘设备管理模块：芯片型号的中文展示名。
// 列表页与详情抽屉都要用，放这里避免页面组件之间互相 import 形成环依赖。
export const EDGE_CHIP_LABEL: Record<string, string> = {
  esp32s3: 'ESP32-S3',
  rk3576: 'RK3576',
  esp32: 'ESP32',
  esp32c3: 'ESP32-C3',
}

// 2026-09-30 雅思口语场景库：Part 编号 → 展示名。约定 ielts_part 为 1/2/3，
// null 表示普通场景。Part 2/3 才有「题卡独白」，Part 1 是逐题追问。
export const IELTS_PART_LABEL: Record<number, string> = {
  1: 'Part 1',
  2: 'Part 2',
  3: 'Part 3',
}

// 雅思根分类名与 Part 子分类名。编辑器据此自动预选 Part，用户仍可手动改。
export const IELTS_ROOT_CATEGORY = '雅思口语'
export const IELTS_PART_CATEGORIES: Record<number, string> = {
  1: 'Part 1',
  2: 'Part 2',
  3: 'Part 3',
}

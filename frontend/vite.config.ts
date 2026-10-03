import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
// 2026-09-29 PWA manifest 的产品名改由 constants.ts 的 PRODUCT_NAME 统一提供
// 2026-10-02 构建修复：tsconfig.node.json 是 module: nodenext，相对导入必须带扩展名
// （该配置同时开了 allowImportingTsExtensions，直接带 .ts 即可，Vite 照常解析）
import { PRODUCT_NAME } from './src/lib/constants.ts'

export default defineConfig({
  // 2026-10-02 收尾轮：数字人 chunk（three.js + VRM，已由 lazy() 单独拆分）gzip 后约 194KB，
  // 超过 Vite 默认 500KB 警戒线，每次构建都刷一条告警。阈值调到 900 让输出干净，
  // 不改变产物本身——那 700 多 KB 是 3D 功能的固有成本
  build: { chunkSizeWarningLimit: 900 },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png'],
      manifest: {
        name: PRODUCT_NAME,
        short_name: PRODUCT_NAME,
        description: '全领域AI学习伙伴',
        // 2026-10-02 第三批品牌统一漏网点：manifest 里还是旧 slate+indigo 配色
        // （#6366f1 / #0f172a），与 zinc+teal 主体系割裂。PWA 安装后标题栏/
        // 启动屏会用到这两个色，随 favicon、登录页一起统一
        theme_color: '#0d9488',       // Teal-600
        background_color: '#09090b',  // Zinc-950
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
        ws: true,
      },
    },
  },
})

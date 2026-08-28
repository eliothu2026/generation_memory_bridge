import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 离线演示模式下无需后端:前端直接 fetch public/demo_script.json。
// 下面的 proxy 仅供 Phase 2「实时(后端)」模式使用,离线模式不受影响。
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // 监听 IPv4+IPv6(0.0.0.0 + ::),避免只绑到 [::1] 导致浏览器 localhost 打不开
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})

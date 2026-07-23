import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const LG_PROXY = {
  target: 'http://127.0.0.1:8123',
  changeOrigin: true,
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  optimizeDeps: {
    exclude: ["@sqlite.org/sqlite-wasm"],
  },
  server: {
    proxy: {
      '/admin': 'http://localhost:8000',
      '/api': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
      '/openapi.json': 'http://localhost:8001',
      '/threads': LG_PROXY,
      '/assistants': LG_PROXY,
      '/runs': LG_PROXY,
      '/crons': LG_PROXY,
      '/store': LG_PROXY,
    },
  },
  preview: {
    proxy: {
      '/admin': 'http://localhost:8000',
      '/api': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
      '/openapi.json': 'http://localhost:8001',
      '/threads': LG_PROXY,
      '/assistants': LG_PROXY,
      '/runs': LG_PROXY,
      '/crons': LG_PROXY,
      '/store': LG_PROXY,
    },
  },
})

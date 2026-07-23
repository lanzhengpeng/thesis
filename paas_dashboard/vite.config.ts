import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const LG_PROXY = {
  target: 'http://127.0.0.1:8123',
  changeOrigin: true,
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/admin': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
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
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/threads': LG_PROXY,
      '/assistants': LG_PROXY,
      '/runs': LG_PROXY,
      '/crons': LG_PROXY,
      '/store': LG_PROXY,
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

const LG_PROXY = {
  target: 'http://127.0.0.1:8123',
  changeOrigin: true,
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@vueuse/integrations/useFocusTrap': path.resolve(__dirname, 'src/utils/useFocusTrapStub.ts'),
    },
  },
  optimizeDeps: {
    exclude: ["@sqlite.org/sqlite-wasm"],
  },
  server: {
    proxy: {
      '/admin': 'http://localhost:8000',
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
      '/threads': LG_PROXY,
      '/assistants': LG_PROXY,
      '/runs': LG_PROXY,
      '/crons': LG_PROXY,
      '/store': LG_PROXY,
    },
  },
})

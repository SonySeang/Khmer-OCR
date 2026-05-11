import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const BACKEND = 'http://localhost:5001'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/process': { target: BACKEND, changeOrigin: true, timeout: 0, proxyTimeout: 0 },
      '/upload':        BACKEND,
      '/process-local': BACKEND,
      '/download':      BACKEND,
      '/documents':     BACKEND,
      '/correct':       BACKEND,
      '/history':       BACKEND,
      '/corrections':   BACKEND,
      '/api':           BACKEND,
    }
  }
})

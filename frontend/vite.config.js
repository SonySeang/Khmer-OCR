import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/process': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0,
      },
      '/upload': 'http://localhost:5001',
      '/process-local': 'http://localhost:5001',
      '/download': 'http://localhost:5001',
      '/documents': 'http://localhost:5001',
    }
  }
})

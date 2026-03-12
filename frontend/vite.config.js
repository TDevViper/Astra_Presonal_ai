import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat':      { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/memory':    { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/health':    { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/model':     { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/mode':      { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/execute':   { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/voice':     { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/vision':    { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/knowledge': { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/realtime':  { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/system':    { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/capabilities': { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/face':      { target: 'http://127.0.0.1:5050', changeOrigin: true },
      '/ws': {
        target: 'ws://127.0.0.1:5050',
        changeOrigin: true,
        ws: true,
      },
    }
  }
})
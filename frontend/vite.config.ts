/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In docker-compose the API is reachable as http://backend:8000; locally it is localhost.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    proxy: { '/api': apiTarget },
  },
  build: {
    rollupOptions: {
      output: {
        // ECharts is most of the bundle and changes rarely: give it its own long-cached chunk.
        manualChunks: (id) =>
          /node_modules[\\/](echarts|zrender)[\\/]/.test(id) ? 'echarts' : undefined,
      },
    },
    chunkSizeWarningLimit: 700,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})

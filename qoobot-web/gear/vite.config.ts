import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3006,
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
    },
  },
})

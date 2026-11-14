import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy /api requests to Django backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React runtime — loaded on every page
          'vendor': ['react', 'react-dom'],
          // Router — separate so non-SPA entry points don't pull it in
          'router': ['react-router-dom'],
          // Data-fetching layer
          'vendor-query': ['@tanstack/react-query'],
          // Charts — largest third-party dependency; defer until a report page loads
          'vendor-charts': ['recharts'],
        },
      },
    },
  },
})

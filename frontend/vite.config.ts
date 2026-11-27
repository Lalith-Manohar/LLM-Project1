/// <reference types="vitest" />
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Preserve localhost:5173 so backend CORS and start.ps1 continue to work seamlessly.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: 'localhost',
    open: false,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    globals: false,
  },
})

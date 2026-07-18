/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  base: '/blender',
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    allowedHosts: true,
    proxy: {
      '/blender/ws': {
        target: 'ws://localhost:19505',
        ws: true,
        rewrite: (path: string) => path.replace(/^\/blender/, ''),
      },
      '/blender/mcp': {
        target: 'http://localhost:19505',
        changeOrigin: false,
        rewrite: (path: string) => path.replace(/^\/blender/, ''),
      },
      '/blender/api': {
        target: 'http://localhost:19505',
        rewrite: (path: string) => path.replace(/^\/blender/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})

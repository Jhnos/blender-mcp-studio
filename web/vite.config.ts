/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backendProxy = {
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
}

// https://vite.dev/config/
export default defineConfig({
  base: '/blender',
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    allowedHosts: true,
    proxy: backendProxy,
  },
  preview: {
    host: '127.0.0.1',
    allowedHosts: true,
    proxy: backendProxy,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})

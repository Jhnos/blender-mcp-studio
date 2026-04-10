import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  base: '/blender',
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    proxy: {
      '/blender/ws': {
        target: 'ws://localhost:17823',
        ws: true,
        rewrite: (path: string) => path.replace(/^\/blender/, ''),
      },
      '/blender/api': {
        target: 'http://localhost:17823',
        rewrite: (path: string) => path.replace(/^\/blender/, ''),
      },
    },
  },
})

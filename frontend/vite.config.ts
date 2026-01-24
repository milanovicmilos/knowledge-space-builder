import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    minify: false
  },
  optimizeDeps: {
    exclude: ['elkjs']
  },
  worker: {
    format: 'es' // Ensure ESM format for web workers
  }
})

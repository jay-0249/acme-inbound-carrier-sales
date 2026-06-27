import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    // Proxy API calls to the FastAPI backend during development
    proxy: {
      '/metrics':        'http://localhost:8000',
      '/loads':          'http://localhost:8000',
      '/calls':          'http://localhost:8000',
      '/negotiate':      'http://localhost:8000',
      '/verify-carrier': 'http://localhost:8000',
    },
  },
})

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/* Dev: proxy /api straight to FastAPI, so server/proxy.js is optional */
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } } },
});

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Builds straight into ../frontend so FastAPI's existing StaticFiles mount
// (main.py: app.mount("/static", StaticFiles(directory="frontend"))) and its
// `/` route (FileResponse("frontend/index.html")) keep working unmodified.
export default defineConfig({
  plugins: [react()],
  base: '/static/',
  build: {
    outDir: '../frontend',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/execute-task': 'http://127.0.0.1:8000',
      '/approve-and-run': 'http://127.0.0.1:8000',
      '/reject-task': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
});

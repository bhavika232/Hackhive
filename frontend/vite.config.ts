import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 3000, strictPort: true },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  build: { rollupOptions: { output: { manualChunks: {
    react: ['react', 'react-dom', 'react-router-dom'],
    ui: ['@mui/material'],
    charts: ['recharts'],
  } } } },
});

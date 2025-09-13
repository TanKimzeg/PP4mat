import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    open: true,
    proxy: {
      '/upload': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});

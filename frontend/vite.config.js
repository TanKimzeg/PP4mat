import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const API_TARGET = 'http://localhost:8000';

const pkgJsonPath = fileURLToPath(new URL('./package.json', import.meta.url));
const pkg = JSON.parse(readFileSync(pkgJsonPath, 'utf-8'));

export default defineConfig({
  plugins: [react()],
  define: {
    // 注入到 import.meta.env.VITE_APP_VERSION
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(pkg.version),
  },
  server: {
    open: true,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});

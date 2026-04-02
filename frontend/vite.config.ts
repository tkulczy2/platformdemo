import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// GitHub project Pages: set VITE_BASE=/repo-name/ in CI. Local dev defaults to /.
function normalizeBase(v: string | undefined): string {
  if (!v?.trim()) return '/';
  let b = v.trim();
  if (!b.startsWith('/')) b = `/${b}`;
  if (!b.endsWith('/')) b = `${b}/`;
  return b;
}

const base = normalizeBase(process.env.VITE_BASE);

export default defineConfig({
  base,
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});

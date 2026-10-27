import { defineConfig } from 'vite';

export default defineConfig({
  publicDir: false,
  server: {
    proxy: {
      '/scenes': 'http://127.0.0.1:8767',
    },
  },
  build: {
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name][extname]',
      },
    },
  },
});

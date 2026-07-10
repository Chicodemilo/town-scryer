// ==============================================================================
// File:      frontend/vite.config.js
// Purpose:   Vite configuration — React plugin, dev server settings, build
//            output with cache-busting filenames, and Vitest test environment.
// Callers:   Vite CLI (dev, build, test)
// Callees:   @vitejs/plugin-react
// Modified:  2026-04-22
// ==============================================================================
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
        chunkFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
        assetFileNames: `assets/[name]-[hash]-${Date.now()}.[ext]`,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.js',
  }
})
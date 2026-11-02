import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In development, Vite serves the app and proxies API calls to FastAPI
// (uvicorn on :8000). In production FastAPI serves the built `dist/`.
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/docs": backend,
      "/openapi.json": backend,
      "/health": backend,
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api/risk": { target: "http://127.0.0.1:19001", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/risk/, "") },
      "/api/recon": { target: "http://127.0.0.1:19002", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/recon/, "") },
      "/api/status": { target: "http://127.0.0.1:19003", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/status/, "") },
      "/api/portfolio": { target: "http://127.0.0.1:19004", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/portfolio/, "") },
      "/api/dms": { target: "http://127.0.0.1:19005", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/dms/, "") },
      "/api/allocator": { target: "http://127.0.0.1:19006", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/allocator/, "") },
      "/api/tca": { target: "http://127.0.0.1:19007", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/tca/, "") },
      "/api/sign": { target: "http://127.0.0.1:19010", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/sign/, "") },
    },
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true
  },
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: {
      "/config": "http://127.0.0.1:8080",
      "/actions": "http://127.0.0.1:8080",
      "/state": "http://127.0.0.1:8080",
      "/status": "http://127.0.0.1:8080",
      "/ui/bootstrap": "http://127.0.0.1:8080",
      "/ui/sessions": "http://127.0.0.1:8080",
      "/ui/snapshot": "http://127.0.0.1:8080"
    }
  }
});

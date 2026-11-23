import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, /api/* is proxied to the FastAPI server so the browser sees a single origin
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});

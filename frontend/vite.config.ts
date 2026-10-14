import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies API and media calls to the backend, so the browser sees ONE origin
// (same as production, where FastAPI serves everything) → cookies work, no CORS needed.
const target = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": target, "/media": target },
  },
});

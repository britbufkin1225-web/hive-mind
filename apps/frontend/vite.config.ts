import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Load env files from the repository root, where `.env.example` lives, so a
  // root-level `.env` actually overrides VITE_API_BASE_URL. Vite's default
  // envDir is this package (apps/frontend); without this, the documented
  // root `.env` is silently ignored.
  envDir: "../..",
  server: {
    port: 5173,
    strictPort: true,
  },
});


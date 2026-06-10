/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Static, local-only app: no proxy, no analytics, no network plugins.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    globals: true,
    // Use jsdom for component tests; the engine parity test uses node-compatible
    // globals only so it works with jsdom too.
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});

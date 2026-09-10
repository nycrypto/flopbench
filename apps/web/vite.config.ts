import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
  },
  test: {
    exclude: [...configDefaults.exclude, "e2e/**"],
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      thresholds: {
        lines: 85,
        functions: 85,
        statements: 85,
        branches: 85,
      },
    },
  },
});

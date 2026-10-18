import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const API_PATH_PREFIXES = ["/auth", "/organizations", "/deals"];

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";
  const proxy = Object.fromEntries(
    API_PATH_PREFIXES.map((prefix) => [prefix, { target: apiTarget, changeOrigin: true }]),
  );

  return {
    plugins: [react()],
    server: { proxy },
    test: {
      environment: "happy-dom",
      setupFiles: ["./src/test-setup.ts"],
    },
  };
});

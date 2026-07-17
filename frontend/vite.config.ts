import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";
  const useHttps = env.VITE_DEV_HTTPS === "true";

  return {
    plugins: [react(), ...(useHttps ? [basicSsl()] : [])],
    server: {
      host: "0.0.0.0",
      port: 5173,
      https: useHttps,
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
          ws: true,
        },
      },
    },
  };
});

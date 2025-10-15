import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      host: true,
      port: Number(env.PORT ?? 5174)
    },
    preview: {
      host: true,
      port: Number(env.PORT ?? 5174)
    }
  };
});

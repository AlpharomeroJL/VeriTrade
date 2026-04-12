import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "../../", "");
  const port = Number(env.VERITRADE_WEB_PORT || 34110);
  return {
    plugins: [react()],
    server: {
      port,
      strictPort: true,
      host: true,
    },
    envDir: "../../",
    envPrefix: ["VITE_", "VERITRADE_"],
  };
});

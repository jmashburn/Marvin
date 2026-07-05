import { defineConfig } from "astro/config";

const apiTarget = process.env.MARVIN_API_URL || "http://localhost:8080";

export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 4321,
  },
  vite: {
    server: {
      proxy: {
        "/api": apiTarget,
      },
    },
  },
});

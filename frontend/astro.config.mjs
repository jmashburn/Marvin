import { defineConfig } from "astro/config";

export default defineConfig({
  output: "server", // Enable server-side rendering for API routes
  server: {
    host: "127.0.0.1",
    port: 4321,
  },
});

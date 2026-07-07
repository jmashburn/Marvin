import { defineConfig } from "astro/config";
import node from "@astrojs/node";

export default defineConfig({
  output: "server", // Enable server-side rendering for API routes
  adapter: node({
    mode: "standalone"
  }),
  server: {
    host: "127.0.0.1",
    port: 4321,
  },
});

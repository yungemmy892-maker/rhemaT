// Standalone Vite + TanStack Start configuration.
//
// This project originally used @lovable.dev/vite-tanstack-config, a preset
// that bundled tanstackStart, @vitejs/plugin-react, @tailwindcss/vite,
// vite-tsconfig-paths, and Nitro (targeting Cloudflare Workers by default)
// behind a single defineConfig() call, plus a dev-only "componentTagger"
// plugin used by Lovable's visual editor. That preset has been removed
// since it depends on a Lovable-hosted package; this file configures the
// same underlying plugins directly so the app builds and runs standalone.
//
// Nitro is configured with the "node-server" preset (a standard Node.js
// server build) rather than Cloudflare, since this app now pairs with a
// self-hosted Django + MongoDB backend rather than Cloudflare Workers.
// Change `nitro.preset` below if you deploy elsewhere (see
// https://nitro.build/deploy for available presets).
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import viteReact from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [
    tsConfigPaths({
      projects: ["./tsconfig.json"],
    }),
    tailwindcss(),
    tanstackStart({
      // Redirect TanStack Start's bundled server entry to src/server.ts
      // (our SSR error wrapper).
      server: { entry: "server" },
    }),
    nitro({
      preset: "node-server",
    }),
    viteReact(),
  ],
});

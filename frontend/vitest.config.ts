import { defineConfig } from "vitest/config";
import { fileURLToPath, URL } from "node:url";

// Deliberately separate from vite.config.ts: mixing vitest's bundled `vite` types with
// @vitejs/plugin-react's `Plugin` type (from the top-level `vite`) breaks `tsc -b` with
// a version-mismatch error. Tests don't need the React or Tailwind plugins — esbuild
// already handles JSX/TSX transform natively, and `css: true` below is enough for CSS
// imports to resolve without erroring.
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    css: true,
  },
});

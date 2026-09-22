import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  root: resolve(import.meta.dirname),
  build: {
    outDir: resolve(import.meta.dirname, "../app/ui/assets"),
    emptyOutDir: false,
    sourcemap: true,
    rollupOptions: {
      input: resolve(import.meta.dirname, "src/main.jsx"),
      output: {
        entryFileNames: "app.js",
        assetFileNames: assetInfo =>
          assetInfo.names?.some(name => name.endsWith(".css"))
            ? "app.css"
            : "[name][extname]",
      },
    },
  },
});

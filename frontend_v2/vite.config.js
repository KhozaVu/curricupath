import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  root: resolve(import.meta.dirname),
  // Served beside the existing UI: /v2 is the new interface, / is unchanged.
  base: "/v2/assets/",
  resolve: { dedupe: ["react", "react-dom", "react/jsx-runtime", "three"] },
  build: {
    outDir: resolve(import.meta.dirname, "../app/ui/assets_v2"),
    emptyOutDir: false,
    // One named stylesheet prevents code-split CSS assets overwriting font faces.
    cssCodeSplit: false,
    sourcemap: true,
    rollupOptions: {
      input: resolve(import.meta.dirname, "src/main.jsx"),
      output: {
        // Keep shared runtime outside the cache-busted entry URL. Otherwise a
        // lazy chunk can import app.js again and create a second React runtime.
        manualChunks(id) {
          if (id.includes("node_modules/@paper-design/")) return "liquid-brand";
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "react-runtime";
          if (/frontend(?:_v2)?\/src\/(webgl\.js|planModel\.mjs|GraphicsBoundary\.jsx)$/.test(id)) return "interface-shared";
          // Lazy review views share controls with the app. Keep those exports
          // outside main.jsx so they never import and execute the bootstrap
          // again through its unversioned URL.
          if (/frontend(?:_v2)?\/src\//.test(id) && !/\/(main|InterfaceSpecimens|AmbientGradient|CurriculumMap)\.jsx$/.test(id)) return "interface-application";
        },
        entryFileNames: "app.js",
        chunkFileNames: "[name]-[hash].js",
        assetFileNames: assetInfo =>
          assetInfo.names?.some(name => name.endsWith(".css"))
            ? "app.css"
            : "[name][extname]",
      },
    },
  },
});

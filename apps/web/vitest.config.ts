import {fileURLToPath} from "node:url";
import {defineConfig} from "vitest/config";

export default defineConfig({
  esbuild: {
    // Next's tsconfig uses jsx:"preserve" (SWC compiles it); vitest needs the
    // automatic JSX runtime so .tsx tests can render without importing React.
    jsx: "automatic",
    jsxImportSource: "react",
  },
  resolve: {
    alias: {"@": fileURLToPath(new URL(".", import.meta.url))},
  },
  test: {
    environment: "happy-dom",
    include: ["tests/**/*.test.{ts,tsx}"],
  },
});

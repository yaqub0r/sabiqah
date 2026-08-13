import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@sabiqah/editor": fileURLToPath(
        new URL("./packages/editor/src/index.ts", import.meta.url),
      ),
      "@sabiqah/release-model": fileURLToPath(
        new URL("./packages/release-model/src/index.ts", import.meta.url),
      ),
    },
  },
  test: {
    include: [
      "apps/**/*.test.{ts,tsx}",
      "packages/**/*.test.{ts,tsx}",
      "workers/**/*.test.{ts,tsx}",
    ],
  },
});

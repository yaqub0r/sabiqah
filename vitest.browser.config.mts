import { playwright } from "@vitest/browser-playwright";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      react: fileURLToPath(
        new URL("./apps/web/node_modules/react", import.meta.url),
      ),
      "react-dom": fileURLToPath(
        new URL("./apps/web/node_modules/react-dom", import.meta.url),
      ),
      "@sabiqah/editor": fileURLToPath(
        new URL("./packages/editor/src/index.ts", import.meta.url),
      ),
      "@sabiqah/release-model": fileURLToPath(
        new URL("./packages/release-model/src/index.ts", import.meta.url),
      ),
    },
  },
  test: {
    include: ["tests/visual/**/*.browser.test.tsx"],
    browser: {
      enabled: true,
      headless: true,
      provider: playwright(),
      screenshotDirectory: ".runtime/visual-qa",
      screenshotFailures: true,
      instances: [
        {
          browser: "chromium",
          name: "mobile-390",
          viewport: { width: 390, height: 844 },
        },
        {
          browser: "chromium",
          name: "tablet-1024",
          viewport: { width: 1024, height: 768 },
        },
        {
          browser: "chromium",
          name: "desktop-1440",
          viewport: { width: 1440, height: 900 },
        },
      ],
    },
  },
});

import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CorpusReader } from "../../apps/web/src/components/CorpusReader";
import "../../apps/web/src/styles/global.css";

const corpusId = "al-isabah-visual-fixture";
const sourceCommit = "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178";

let root: Root;

function response(body: unknown, ok = true) {
  return Promise.resolve({ ok, json: async () => body });
}

async function waitForVolumeShelf() {
  const deadline = Date.now() + 5_000;
  while (Date.now() < deadline) {
    const buttons = document.querySelectorAll<HTMLButtonElement>(
      ".volume-shelf button",
    );
    if (buttons.length === 7) return [...buttons];
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error("The deterministic volume fixture did not render.");
}

function rectanglesOverlap(a: DOMRect, b: DOMRect) {
  return (
    a.left < b.right - 1 &&
    a.right > b.left + 1 &&
    a.top < b.bottom - 1 &&
    a.bottom > b.top + 1
  );
}

beforeEach(() => {
  document.body.innerHTML = '<main class="shell" id="visual-root"></main>';
  window.history.replaceState(null, "", "/works/al-isabah/");

  const volumes = [2, 3, 4, 5, 6, 7, 8].map((number) => ({
    id: `volume-${String(number).padStart(2, "0")}`,
    number,
    label: `Volume ${number}`,
    availability: "complete_translation",
    itemCount: number === 7 ? 672 : number === 8 ? 879 : number,
    sectionCount: 1,
    firstPrintedPage: 1,
    lastPrintedPage: 25,
    description: "Partial working coverage.",
  }));

  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const path = typeof input === "string" ? input : input.toString();
      if (path === "/api/session") return response({}, false);
      if (path === "/api/corpus/al-isabah/summary") {
        return response({
          schemaVersion: "2.0.0",
          work: {
            slug: "al-isabah",
            titleAr: "الإصابة في تمييز الصحابة",
            titleEn: "Al-Isabah fi Tamyiz al-Sahabah",
          },
          corpus: {
            id: corpusId,
            sourceRepository: "https://github.com/yaqub0r/al-isabah",
            sourceCommit,
            generatedAt: "2026-08-13T00:00:00.000Z",
            promotionStatus: "blocked",
          },
          counts: {
            entries: 1_565,
            passages: 0,
            translated: 1_565,
            needsAttention: 0,
            unresolvedItems: 310,
            humanReviewed: 0,
          },
          exclusions: {
            contextualPassagesPendingPublicSourceAlignment: 14,
            recordsPendingRemediation: 0,
          },
          volumes,
        });
      }
      if (path === "/api/corpus/al-isabah/index") {
        return response({ schemaVersion: "2.0.0", corpusId, items: [] });
      }
      if (path === "/api/corpus/al-isabah/reviews") {
        return response({ corpusId, reviewedItems: 0, items: {} });
      }
      return response({}, false);
    }),
  );

  root = createRoot(document.getElementById("visual-root")!);
});

afterEach(() => {
  root.unmount();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("CorpusReader presentation quality", () => {
  it("keeps the volume selector legible and collision-free", async () => {
    root.render(<CorpusReader />);
    const buttons = await waitForVolumeShelf();
    const width = document.documentElement.clientWidth;
    const expectedColumns = width >= 1_200 ? 8 : width <= 720 ? 2 : 4;
    const shelf = document.querySelector<HTMLElement>(".volume-shelf")!;
    const actualColumns =
      getComputedStyle(shelf).gridTemplateColumns.split(" ");

    expect(actualColumns).toHaveLength(expectedColumns);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );

    for (const [index, button] of buttons.entries()) {
      expect(
        button.scrollWidth,
        `volume button ${index + 2} width`,
      ).toBeLessThanOrEqual(button.clientWidth);
      expect(
        button.scrollHeight,
        `volume button ${index + 2} height`,
      ).toBeLessThanOrEqual(button.clientHeight);

      const buttonRect = button.getBoundingClientRect();
      for (const child of button.children) {
        const childRect = child.getBoundingClientRect();
        expect(childRect.left).toBeGreaterThanOrEqual(buttonRect.left - 1);
        expect(childRect.right).toBeLessThanOrEqual(buttonRect.right + 1);
      }

      for (const other of buttons.slice(index + 1)) {
        expect(
          rectanglesOverlap(buttonRect, other.getBoundingClientRect()),
        ).toBe(false);
      }
    }

    const selected = document.querySelector<HTMLButtonElement>(
      '.volume-shelf button[aria-pressed="true"]',
    );
    expect(selected?.getAttribute("aria-label")).toBe(
      "Volume 8, 879 records, partial coverage",
    );
    expect(selected?.textContent).toContain("Volume");
    expect(selected?.textContent).toContain("8");
  });
});

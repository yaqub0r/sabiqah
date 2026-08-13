import { createRoot, type Root } from "react-dom/client";
import { page } from "vitest/browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CorpusReader } from "../../apps/web/src/components/CorpusReader";
import "../../apps/web/src/styles/global.css";

const corpusId = "al-isabah-visual-fixture";
const sourceCommit = "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178";
const sectionId = "volume-08-pages-0001-0025";

function record(
  id: string,
  number: number,
  titleEn: string,
  titleAr: string,
  english: string,
) {
  return {
    schemaVersion: "2.0.0",
    corpusId,
    id,
    kind: "entry",
    sequence: number,
    printedEntryNumber: number,
    volume: 8,
    title: { en: titleEn, ar: titleAr },
    translationState: "translated",
    machineAssessment: "passed",
    humanReview: "unreviewed",
    segments: [
      {
        id: `${id}-segment-0001`,
        arabic: "نص عربي للقراءة واختبار بنية المدخل.",
        english,
        pages: [
          {
            volume: 8,
            printedPage: 1,
            readerPage: null,
            providerPage: "https://github.com/OpenITI/0875AH",
          },
        ],
        machineState: "machine_validated_unreviewed",
      },
    ],
    names: [],
    unresolved: [],
    workflowStages: [
      {
        stage: "machine_validation",
        state: "complete",
        summary: "Deterministic visual fixture.",
      },
    ],
    provenance: {
      sourceArtifactId: `visual:${number}`,
      sourceArtifactSha256: "a".repeat(64),
    },
  };
}

const shortRecord = record(
  "isabah-entry-00011430",
  11426,
  "Duba'a bint Amir",
  "ضباعة بنت عامر",
  "A short body.",
);
const longRecord = record(
  "isabah-entry-00011443",
  11439,
  "Tufya",
  "طفية",
  "A deliberately longer body. ".repeat(12) +
    "It introduces the following verse:\n\n" +
    "The first translated line of poetry,\nthe second translated line of poetry.\n\n" +
    "Another measured pair of lines,\nset apart for deliberate reading.\n\n" +
    "Meter: al-Tawil\n\n" +
    "The prose account then continues.",
);
const structuredRecord = {
  ...longRecord,
  segments: longRecord.segments.map((segment) => ({
    ...segment,
    arabic: "نثر تمهيدي للقراءة:\nبيت أول من الشعر\nبيت ثان من الشعر",
  })),
  headingsBefore: [
    { level: "letter", en: "Letter Ẓāʾ (ظ)", ar: "حرف الظاء المشالة" },
    {
      level: "section",
      en: "Sections Two and Three",
      ar: "القسم الثاني والقسم الثالث",
      noteEn: "No entries are recorded in either section.",
      noteAr: "لم يذكر فيهما أحد",
    },
  ],
};

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
      if (path === "/api/session") {
        return response({
          identity: {
            login: "visual-reviewer",
            membershipStatus: "active",
          },
        });
      }
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
        return response({
          schemaVersion: "2.0.0",
          corpusId,
          items: [shortRecord, structuredRecord].map((item) => ({
            id: item.id,
            kind: item.kind,
            sequence: item.sequence,
            printedEntryNumber: item.printedEntryNumber,
            volume: item.volume,
            printedPageStart: 1,
            printedPageEnd: 1,
            sectionId,
            titleEn: item.title.en,
            titleAr: item.title.ar,
            translationState: item.translationState,
            machineAssessment: item.machineAssessment,
            humanReview: item.humanReview,
            unresolvedCount: 0,
          })),
        });
      }
      if (path === "/api/corpus/al-isabah/reviews") {
        return response({ corpusId, reviewedItems: 0, items: {} });
      }
      if (path === "/api/corpus/al-isabah/reports") {
        return response({
          issue: {
            number: 91,
            url: "https://github.com/yaqub0r/sabiqah/issues/91",
          },
        });
      }
      if (path === `/api/corpus/al-isabah/sections/${sectionId}`) {
        return response({
          schemaVersion: "2.0.0",
          corpusId,
          id: sectionId,
          volume: 8,
          label: "Pages 1–25",
          availability: "complete_translation",
          position: 1,
          totalSections: 1,
          printedPageStart: 1,
          printedPageEnd: 1,
          previousSectionId: null,
          nextSectionId: null,
          items: [shortRecord, structuredRecord],
        });
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

  it("keeps entry-title typography independent of body length", async () => {
    root.render(<CorpusReader />);
    const deadline = Date.now() + 5_000;
    let headings: HTMLElement[] = [];
    while (Date.now() < deadline) {
      headings = [
        ...document.querySelectorAll<HTMLElement>(".reading-record h3"),
      ];
      if (headings.length === 2) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    expect(headings).toHaveLength(2);
    expect(
      headings.map((heading) => getComputedStyle(heading).fontSize),
    ).toEqual([
      getComputedStyle(headings[0]!).fontSize,
      getComputedStyle(headings[0]!).fontSize,
    ]);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    for (const [index, heading] of headings.entries()) {
      const header = heading.closest<HTMLElement>("header");
      expect(header).not.toBeNull();
      await page.screenshot({
        element: header!,
        path: `../../.runtime/visual-qa/entry-title-${document.documentElement.clientWidth}-${index === 0 ? "short" : "long"}.png`,
      });
    }
  });

  it("keeps source-structure headings distinct and collision-free", async () => {
    root.render(<CorpusReader />);
    const deadline = Date.now() + 5_000;
    let heading: HTMLElement | null = null;
    while (Date.now() < deadline) {
      heading = document.querySelector<HTMLElement>(
        ".source-structure-heading",
      );
      if (heading) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    expect(heading).not.toBeNull();
    expect(heading?.textContent).toContain("Letter Ẓāʾ (ظ)");
    expect(heading?.textContent).toContain("حرف الظاء المشالة");
    expect(heading?.textContent).toContain(
      "No entries are recorded in either section.",
    );
    expect(heading?.scrollWidth).toBeLessThanOrEqual(heading!.clientWidth);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    const blocks = [...heading!.children].map((child) =>
      child.getBoundingClientRect(),
    );
    if (blocks.length > 1 && blocks[0]!.top === blocks[1]!.top) {
      expect(rectanglesOverlap(blocks[0]!, blocks[1]!)).toBe(false);
    }
    await page.screenshot({
      element: heading!,
      path: `../../.runtime/visual-qa/source-structure-${document.documentElement.clientWidth}.png`,
    });
  });

  it("distinguishes bilingual poetry without clipping or overflow", async () => {
    root.render(<CorpusReader />);
    const deadline = Date.now() + 5_000;
    let poetry: HTMLElement | null = null;
    while (Date.now() < deadline) {
      poetry = document.querySelector<HTMLElement>(".poetry-block");
      if (poetry) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    expect(poetry).not.toBeNull();
    expect(poetry?.textContent).toContain("Meter: al-Tawil");
    expect(
      getComputedStyle(poetry!.querySelector("blockquote")!).fontStyle,
    ).toBe("italic");
    expect(document.querySelectorAll(".arabic-poetry p")).toHaveLength(2);
    expect(poetry?.scrollWidth).toBeLessThanOrEqual(poetry!.clientWidth);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    await page.screenshot({
      element: poetry!.closest<HTMLElement>(".reading-bilingual")!,
      path: `../../.runtime/visual-qa/poetry-${document.documentElement.clientWidth}.png`,
    });
  });

  it("keeps the selected-text action and report dialog usable", async () => {
    root.render(<CorpusReader />);
    await waitForVolumeShelf();
    const deadline = Date.now() + 5_000;
    let paragraph: HTMLElement | null = null;
    while (Date.now() < deadline) {
      paragraph = document.querySelector<HTMLElement>(
        '[data-report-language="English"] .corpus-text',
      );
      if (paragraph) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
    expect(paragraph).not.toBeNull();
    const text = document
      .createTreeWalker(paragraph!, NodeFilter.SHOW_TEXT)
      .nextNode();
    expect(text).not.toBeNull();
    const range = document.createRange();
    range.setStart(text!, 0);
    range.setEnd(text!, Math.min(18, text!.textContent!.length));
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    document.dispatchEvent(new Event("selectionchange"));

    const action = await page.getByRole("button", {
      name: "Report selected text",
    });
    await expect.element(action).toBeVisible();
    await action.click();
    const dialog = document.querySelector<HTMLElement>(
      ".selection-report-dialog",
    );
    expect(dialog).not.toBeNull();
    expect(dialog!.scrollWidth).toBeLessThanOrEqual(dialog!.clientWidth);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    await page.screenshot({
      path: `../../.runtime/visual-qa/selection-report-${document.documentElement.clientWidth}.png`,
    });
  });
});

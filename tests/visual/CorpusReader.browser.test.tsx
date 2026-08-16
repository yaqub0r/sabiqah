import { createRoot, type Root } from "react-dom/client";
import { page } from "vitest/browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CorpusReader } from "../../apps/web/src/components/CorpusReader";
import { CorpusCoverage } from "../../apps/web/src/components/CorpusCoverage";
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
    cohortId: "distribution:synthetic-v2",
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
    source: {
      authorityId: "al-isabah-openiti-5835c18-aco-v1",
      producerAuthorityId: "openiti-cleaned-arabic-comparison",
      entryNumber: number,
      pages: ["V08P001"],
      sourceTextSha256: "b".repeat(64),
      sourceUrl: "https://github.com/OpenITI/0875AH",
      license: {
        spdx: "CC-BY-NC-SA-4.0",
        url: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
      },
      attribution: "OpenITI synthetic visual fixture",
      englishRights: {
        license: {
          spdx: "CC-BY-NC-SA-4.0",
          url: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        },
        attribution: "Al-Isabah synthetic English visual fixture",
      },
      rightsMatrix: {
        id: "al-isabah-rights-synthetic",
        schema: "al-isabah.book-rights-matrix.v1",
        decision: "approved-under-cc-by-nc-sa-4.0",
        reviewedOn: "2026-08-15",
        followUp: "required-on-change",
      },
      alignment: {
        method: "al-isabah-public-distribution-v2",
        titleScore: 1,
        bodyScore: 1,
      },
    },
    provenance: {
      sourceAuthorityId: "al-isabah-openiti-5835c18-aco-v1",
      producerAuthorityId: "openiti-cleaned-arabic-comparison",
      sourceArtifactSha256: "a".repeat(64),
      sourceTextSha256: "b".repeat(64),
    },
  };
}

const shortRecord = record(
  "isabah-entry-00011430",
  11426,
  "Duba'a bint Amir",
  "ضباعة بنت عامر",
  "al-Tabari mentioned her among those concerning whom the following was revealed: “And do not marry those women whom your fathers married” [al-Nisa': 22].",
);
const contextualRecord = {
  ...shortRecord,
  headingsBefore: [
    {
      level: "letter",
      en: "Letter Ḍād (ض)",
      ar: "حرف الضاد المعجمة",
      context: "continued",
      contextSourceEntryNumber: 11425,
    },
    {
      level: "section",
      en: "Section One",
      ar: "القسم الأول",
      context: "continued",
      contextSourceEntryNumber: 11425,
    },
  ],
};
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
    {
      level: "section",
      en: "Sections Two and Three",
      ar: "القسم الثاني والقسم الثالث",
      noteEn: "No entries are recorded in either section.",
      noteAr: "لم يذكر فيهما أحد",
    },
    { level: "section", en: "Section Four", ar: "الرابع" },
  ],
};

let root: Root;

function response(body: unknown, ok = true) {
  return Promise.resolve({ ok, json: async () => body });
}

async function waitForVolumeShelf() {
  const deadline = Date.now() + 5_000;
  while (Date.now() < deadline) {
    const cards = document.querySelectorAll<HTMLElement>(".coverage-card");
    if (cards.length === 8) return [...cards];
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

  const sourceCounts: Record<number, number> = {
    1: 1536,
    2: 1497,
    3: 1491,
    4: 1633,
    5: 1602,
    6: 1722,
    7: 1938,
    8: 879,
  };
  const volumes = [1, 2, 3, 4, 5, 6, 7, 8].map((number) => {
    const itemCount =
      number === 1 ? 0 : number === 7 ? 672 : number === 8 ? 879 : number;
    return {
      id: `volume-${String(number).padStart(2, "0")}`,
      number,
      label: `Volume ${number}`,
      availability:
        itemCount === sourceCounts[number]
          ? "complete_translation"
          : itemCount === 0
            ? "not_translated"
            : "selected_passages",
      sourceItemCount: sourceCounts[number],
      itemCount,
      sectionCount: itemCount === 0 ? 0 : 1,
      firstPrintedPage: itemCount === 0 ? null : 1,
      lastPrintedPage: itemCount === 0 ? null : 25,
      description: "Deterministic coverage fixture.",
    };
  });

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
          items: [contextualRecord, structuredRecord].map((item) => ({
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
        return response({
          corpusId,
          reviewedItems: 1,
          items: {
            [shortRecord.id]: {
              approvalCount: 1,
              currentUserApproved: true,
              latestApprovalAt: 1,
            },
          },
        });
      }
      if (path === "/api/corpus/al-isabah/progress") {
        return response({ corpusId, readItems: 0, items: {} });
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
          items: [contextualRecord, structuredRecord],
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
  it("keeps the separate coverage dashboard legible and actionable", async () => {
    root.render(<CorpusCoverage />);
    const cards = await waitForVolumeShelf();
    const width = document.documentElement.clientWidth;
    const expectedColumns = width >= 1_200 ? 4 : width <= 720 ? 1 : 2;
    const shelf = document.querySelector<HTMLElement>(".volume-shelf")!;
    const actualColumns =
      getComputedStyle(shelf).gridTemplateColumns.split(" ");

    expect(actualColumns).toHaveLength(expectedColumns);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );

    for (const [index, card] of cards.entries()) {
      expect(
        card.scrollWidth,
        `coverage card ${index + 1} width`,
      ).toBeLessThanOrEqual(card.clientWidth);
      expect(
        card.scrollHeight,
        `coverage card ${index + 1} height`,
      ).toBeLessThanOrEqual(card.clientHeight);

      const cardRect = card.getBoundingClientRect();
      for (const child of card.children) {
        const childRect = child.getBoundingClientRect();
        expect(childRect.left).toBeGreaterThanOrEqual(cardRect.left - 1);
        expect(childRect.right).toBeLessThanOrEqual(cardRect.right + 1);
      }

      for (const other of cards.slice(index + 1)) {
        expect(rectanglesOverlap(cardRect, other.getBoundingClientRect())).toBe(
          false,
        );
      }
    }

    expect(cards[7]?.getAttribute("aria-label")).toBe(
      "Volume 8: 879 of 879 source entries translated; 1 of 879 translations human reviewed; Complete working translation",
    );
    expect(cards[7]?.textContent).toContain("100% translated");
    expect(cards[7]?.textContent).toContain("1 of 879 translations");
    expect(cards[7]?.textContent).toContain("Review remaining translations");
    expect(
      cards[7]
        ?.querySelector<HTMLAnchorElement>('a[href*="review=unreviewed"]')
        ?.getAttribute("href"),
    ).toBe("/works/al-isabah/?volume=8&review=unreviewed");
    expect(cards[0]?.textContent).toContain("Reading not available");
    await page.screenshot({
      element: document.querySelector<HTMLElement>(".edition-overview")!,
      path: `../../.runtime/visual-qa/coverage-dashboard-${width}.png`,
    });
  });

  it("keeps compact volume selection inside the reader", async () => {
    root.render(<CorpusReader />);
    let selector: HTMLSelectElement | null = null;
    const deadline = Date.now() + 5_000;
    while (Date.now() < deadline) {
      selector = document.querySelector<HTMLSelectElement>(
        ".reader-volume-select select",
      );
      if (selector?.options.length) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    expect(selector?.value).toBe("8");
    expect(document.querySelector(".edition-overview")).toBeNull();
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    await page.screenshot({
      element: document.querySelector<HTMLElement>(".book-reader")!,
      path: `../../.runtime/visual-qa/reader-volume-selector-${document.documentElement.clientWidth}.png`,
    });
  });

  it("keeps translation actions compact and usable", async () => {
    root.render(<CorpusReader />);
    const deadline = Date.now() + 5_000;
    let actionBar: HTMLElement | null = null;
    while (Date.now() < deadline) {
      actionBar = document.querySelector<HTMLElement>(".translation-approval");
      if (actionBar?.querySelector("button:not([disabled])")) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    expect(actionBar).not.toBeNull();
    expect(actionBar?.textContent).not.toContain(
      "Approval applies to this English translation",
    );
    expect(actionBar?.textContent).toContain("Mark as read");
    expect(actionBar?.scrollWidth).toBeLessThanOrEqual(actionBar!.clientWidth);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    await page.screenshot({
      element: actionBar!,
      path: `../../.runtime/visual-qa/translation-actions-${document.documentElement.clientWidth}.png`,
    });
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
    let headings: HTMLElement[] = [];
    while (Date.now() < deadline) {
      headings = [
        ...document.querySelectorAll<HTMLElement>(".source-structure-heading"),
      ];
      if (headings.length === 2) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    expect(headings).toHaveLength(2);
    expect(headings[0]?.textContent).toContain("Continued source context");
    expect(headings[0]?.textContent).toContain("Letter Ḍād (ض)");
    expect(headings[0]?.textContent).toContain("Section One");
    expect(headings[1]?.textContent).toContain(
      "No entries are recorded in either section.",
    );
    expect(headings[1]?.textContent).toContain("Section Four");
    for (const heading of headings) {
      expect(heading.scrollWidth).toBeLessThanOrEqual(heading.clientWidth);
    }
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    const rows = [
      ...headings[1]!.querySelectorAll<HTMLElement>(".source-structure-row"),
    ].map((child) => child.getBoundingClientRect());
    expect(rectanglesOverlap(rows[0]!, rows[1]!)).toBe(false);
    await page.screenshot({
      element: headings[0]!,
      path: `../../.runtime/visual-qa/source-context-${document.documentElement.clientWidth}.png`,
    });
    await page.screenshot({
      element: headings[1]!,
      path: `../../.runtime/visual-qa/source-structure-${document.documentElement.clientWidth}.png`,
    });
  });

  it("keeps separate Arabic and English rights readable", async () => {
    root.render(<CorpusReader />);
    const deadline = Date.now() + 5_000;
    let provenance: HTMLElement | null = null;
    while (Date.now() < deadline) {
      provenance = document.querySelector<HTMLElement>(".provenance-line");
      if (provenance?.textContent?.includes("Independently authored English"))
        break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    expect(provenance).not.toBeNull();
    expect(provenance?.textContent).toContain("Arabic source:");
    expect(provenance?.textContent).toContain(
      "Independently authored English:",
    );
    expect(provenance?.textContent).toContain("al-isabah-rights-synthetic");
    expect(provenance?.textContent).toContain("distribution:synthetic-v2");
    provenance!.closest("details")!.open = true;
    await new Promise((resolve) => requestAnimationFrame(resolve));
    expect(provenance?.scrollWidth).toBeLessThanOrEqual(
      provenance!.clientWidth,
    );
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
    await page.screenshot({
      element: provenance!,
      path: `../../.runtime/visual-qa/rights-provenance-${document.documentElement.clientWidth}.png`,
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
    const deadline = Date.now() + 5_000;
    let paragraph: HTMLElement | null = null;
    while (Date.now() < deadline) {
      paragraph =
        [
          ...document.querySelectorAll<HTMLElement>(
            '[data-report-language="English"] .corpus-text',
          ),
        ].find((candidate) =>
          candidate.textContent?.includes("al-Tabari mentioned her"),
        ) ?? null;
      if (paragraph) break;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
    expect(paragraph).not.toBeNull();
    const englishTarget = paragraph!.closest<HTMLElement>(
      '[data-report-language="English"]',
    );
    const arabicTarget =
      englishTarget?.parentElement?.querySelector<HTMLElement>(
        '[data-report-language="Arabic"]',
      );
    expect(englishTarget).not.toBeNull();
    expect(arabicTarget).not.toBeNull();
    const range = document.createRange();
    range.setStart(paragraph!.firstChild!, 0);
    range.setEnd(arabicTarget!, 0);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    paragraph!.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));

    const action = await page.getByRole("button", {
      name: "Report selected text",
    });
    await expect.element(action).toBeVisible();
    const contextMenu = new MouseEvent("contextmenu", {
      bubbles: true,
      cancelable: true,
    });
    paragraph!.dispatchEvent(contextMenu);
    expect(contextMenu.defaultPrevented).toBe(false);
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

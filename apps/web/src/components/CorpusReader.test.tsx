// @vitest-environment jsdom

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { normalizeHonorificSearch } from "@sabiqah/release-model";

import { CorpusReader, englishReadingBlocks } from "./CorpusReader";

const corpusId = "al-isabah-reading-a3b76bf-v3";
const sectionId = "volume-08-pages-0001-0025";

function item(id: string, sequence: number, title: string, sentence: string) {
  return {
    schemaVersion: "2.0.0",
    corpusId,
    id,
    kind: "entry",
    sequence,
    printedEntryNumber: sequence,
    volume: 8,
    title: { en: title, ar: "اسم" },
    translationState: "translated",
    machineAssessment: "passed",
    humanReview: "unreviewed",
    segments: [
      {
        id: `${id}-segment-1`,
        arabic: "نص عربي قصير.",
        english: sentence,
        pages: [
          {
            volume: 8,
            printedPage: 3,
            readerPage: 3916,
            providerPage: "https://usul.ai/t/isaba-fi-tamyiz/3916",
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
        summary: "Machine validation passed.",
      },
    ],
    provenance: {
      sourceArtifactId: `al-isabah:entry:${sequence}`,
      sourceArtifactSha256:
        "f12585cea28d7c7b318728f74b1a95a0d8b2812cb25d6e70f1b9e7b0b9422a3f",
    },
  };
}

const firstItem = item(
  "isabah-entry-00010759",
  10759,
  "First short entry",
  "The first short translated record.",
);
const secondItem = item(
  "isabah-entry-00010760",
  10760,
  "Second short entry",
  "The following short record continues in the same reading section.",
);
const untranslatedItem = {
  ...secondItem,
  title: { ...secondItem.title, en: "Entry 10760" },
  translationState: "untranslated" as const,
  segments: secondItem.segments.map((segment) => ({
    ...segment,
    english: "",
  })),
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

describe("CorpusReader", () => {
  it("requires an explicit meter label before styling text as poetry", () => {
    const prose = englishReadingBlocks(
      "ibn Abd al-Muttalib al-Hashimiyya\n\nal-Daraqutni mentioned her in the Book of Siblings.",
    );

    expect(prose).toEqual([
      { kind: "prose", paragraphs: ["ibn Abd al-Muttalib al-Hashimiyya"] },
      {
        kind: "prose",
        paragraphs: ["al-Daraqutni mentioned her in the Book of Siblings."],
      },
    ]);

    expect(
      englishReadingBlocks(
        "The first verse.\n\nMeter: al-Rajaz\n\nThe prose resumes.",
      ),
    ).toEqual([
      {
        kind: "poetry",
        paragraphs: ["The first verse."],
        meter: "al-Rajaz",
        continuation: undefined,
      },
      { kind: "prose", paragraphs: ["The prose resumes."] },
    ]);
  });

  it("lets anonymous visitors read while keeping approval controls gated", async () => {
    const responses = new Map<string, unknown>([
      [
        "/api/corpus/al-isabah/summary",
        {
          schemaVersion: "2.0.0",
          work: {
            slug: "al-isabah",
            titleAr: "Ø§Ù„Ø¥ØµØ§Ø¨Ø©",
            titleEn: "Al-Isabah fi Tamyiz al-Sahabah",
          },
          corpus: {
            id: corpusId,
            sourceRepository: "https://github.com/yaqub0r/al-isabah",
            sourceCommit: "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178",
            generatedAt: "2026-08-12T00:00:00.000Z",
            promotionStatus: "blocked",
          },
          counts: {
            entries: 2,
            passages: 0,
            translated: 2,
            needsAttention: 0,
            unresolvedItems: 0,
            humanReviewed: 0,
            sourceInventory: 16,
            quarantined: 14,
          },
          exclusions: {
            contextualPassagesPendingPublicSourceAlignment: 14,
            recordsPendingRemediation: 0,
          },
          volumes: [
            {
              id: "volume-08",
              number: 8,
              label: "Volume 8",
              availability: "complete_translation",
              itemCount: 2,
              sectionCount: 1,
              firstPrintedPage: 3,
              lastPrintedPage: 3,
              description: "Complete working translation.",
            },
          ],
        },
      ],
      [
        "/api/corpus/al-isabah/index",
        {
          schemaVersion: "2.0.0",
          corpusId,
          items: [firstItem, secondItem].map((record) => ({
            id: record.id,
            kind: record.kind,
            sequence: record.sequence,
            printedEntryNumber: record.printedEntryNumber,
            volume: record.volume,
            printedPageStart: 3,
            printedPageEnd: 3,
            sectionId,
            titleEn: record.title.en,
            titleAr: record.title.ar,
            translationState: record.translationState,
            machineAssessment: record.machineAssessment,
            humanReview: record.humanReview,
            unresolvedCount: 0,
            searchText: normalizeHonorificSearch(
              `${record.title.en} ${record.segments[0]?.english} ${record === secondItem ? "Muhammad ﷺ" : ""}`,
            ),
          })),
        },
      ],
      [
        "/api/corpus/al-isabah/reviews",
        { corpusId, reviewedItems: 0, items: {} },
      ],
      [
        `/api/corpus/al-isabah/sections/${sectionId}`,
        {
          schemaVersion: "2.0.0",
          corpusId,
          id: sectionId,
          volume: 8,
          label: "Pages 1â€“25",
          availability: "complete_translation",
          position: 1,
          totalSections: 1,
          printedPageStart: 3,
          printedPageEnd: 3,
          previousSectionId: null,
          nextSectionId: null,
          items: [firstItem, secondItem],
        },
      ],
    ]);

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const path = typeof input === "string" ? input : input.toString();
        if (path === "/api/session") {
          return { ok: false, json: async () => ({ error: "anonymous" }) };
        }
        const body = responses.get(path);
        return { ok: body !== undefined, json: async () => body };
      }),
    );

    render(<CorpusReader />);

    expect(
      ((await screen.findByLabelText("Reading volume")) as HTMLSelectElement)
        .value,
    ).toBe("8");
    expect(screen.queryByText("Coverage by source volume")).toBeNull();
    expect(
      await screen.findByText("The first short translated record."),
    ).toBeTruthy();
    expect(
      await screen.findByText(
        "Have an invitation to review or correct the text?",
      ),
    ).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Approve this translation" }),
    ).toBeNull();
    fireEvent.change(
      screen.getByRole("searchbox", { name: "Name or entry number" }),
      { target: { value: "peace and blessings be upon him" } },
    );
    expect(
      screen.getByRole("button", { name: /Second short entry/ }),
    ).toBeTruthy();
  });

  it("renders source headings between records instead of inside biography prose", async () => {
    const headedItem = {
      ...firstItem,
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
    const responses = new Map<string, unknown>([
      [
        "/api/corpus/al-isabah/summary",
        {
          schemaVersion: "2.0.0",
          work: { slug: "al-isabah", titleAr: "الإصابة", titleEn: "Al-Isabah" },
          corpus: {
            id: corpusId,
            sourceRepository: "https://github.com/yaqub0r/al-isabah",
            sourceCommit: "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178",
            generatedAt: "2026-08-12T00:00:00.000Z",
            promotionStatus: "blocked",
          },
          counts: {
            entries: 1,
            passages: 0,
            translated: 1,
            needsAttention: 0,
            unresolvedItems: 0,
            humanReviewed: 0,
          },
          volumes: [
            {
              id: "volume-08",
              number: 8,
              label: "Volume 8",
              availability: "selected_passages",
              itemCount: 1,
              sectionCount: 1,
              firstPrintedPage: 3,
              lastPrintedPage: 3,
              description: "Working translation.",
            },
          ],
        },
      ],
      [
        "/api/corpus/al-isabah/index",
        {
          schemaVersion: "2.0.0",
          corpusId,
          items: [
            {
              id: firstItem.id,
              kind: firstItem.kind,
              sequence: firstItem.sequence,
              printedEntryNumber: firstItem.printedEntryNumber,
              volume: 8,
              printedPageStart: 3,
              printedPageEnd: 3,
              sectionId,
              titleEn: firstItem.title.en,
              titleAr: firstItem.title.ar,
              translationState: "translated",
              machineAssessment: "passed",
              humanReview: "unreviewed",
              unresolvedCount: 0,
            },
          ],
        },
      ],
      [
        "/api/corpus/al-isabah/reviews",
        { corpusId, reviewedItems: 0, items: {} },
      ],
      [
        `/api/corpus/al-isabah/sections/${sectionId}`,
        {
          schemaVersion: "2.0.0",
          corpusId,
          id: sectionId,
          volume: 8,
          label: "Pages 1–25",
          availability: "selected_passages",
          position: 1,
          totalSections: 1,
          printedPageStart: 3,
          printedPageEnd: 3,
          previousSectionId: null,
          nextSectionId: null,
          items: [headedItem],
        },
      ],
    ]);
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/session") return Promise.resolve({ ok: false });
        const body = responses.get(url);
        return Promise.resolve({
          ok: body !== undefined,
          json: async () => body,
        });
      }),
    );

    render(<CorpusReader />);

    expect(
      await screen.findByRole("heading", { name: "Sections Two and Three" }),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Section Four" })).toBeTruthy();
    expect(
      screen.getByText("No entries are recorded in either section."),
    ).toBeTruthy();
    const rows = document.querySelectorAll(".source-structure-row");
    expect(rows).toHaveLength(2);
    expect(rows[0]?.children[0]?.textContent).toContain(
      "Sections Two and Three",
    );
    expect(rows[0]?.children[1]?.textContent).toContain(
      "القسم الثاني والقسم الثالث",
    );
    expect(rows[1]?.children[0]?.textContent).toContain("Section Four");
    expect(rows[1]?.children[1]?.textContent).toContain("الرابع");
    expect(
      document.querySelector(".source-structure-heading + .reading-record"),
    ).toBeTruthy();
  });

  it("presents consecutive short records inside a volume reading section", async () => {
    const responses = new Map<string, unknown>([
      [
        "/api/corpus/al-isabah/summary",
        {
          schemaVersion: "2.0.0",
          work: {
            slug: "al-isabah",
            titleAr: "الإصابة في تمييز الصحابة",
            titleEn: "Al-Isabah fi Tamyiz al-Sahabah",
          },
          corpus: {
            id: corpusId,
            sourceRepository: "https://github.com/yaqub0r/al-isabah",
            sourceCommit: "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178",
            generatedAt: "2026-08-12T00:00:00.000Z",
            promotionStatus: "blocked",
          },
          counts: {
            entries: 2,
            passages: 0,
            translated: 1,
            needsAttention: 0,
            unresolvedItems: 0,
            humanReviewed: 0,
          },
          volumes: [
            {
              id: "volume-08",
              number: 8,
              label: "Volume 8",
              availability: "complete_translation",
              itemCount: 2,
              sectionCount: 1,
              firstPrintedPage: 3,
              lastPrintedPage: 3,
              description: "Complete working translation.",
            },
          ],
        },
      ],
      [
        "/api/session",
        {
          identity: {
            login: "reader",
            membershipStatus: "active",
          },
        },
      ],
      [
        "/api/corpus/al-isabah/index",
        {
          schemaVersion: "2.0.0",
          corpusId,
          items: [firstItem, untranslatedItem].map((record) => ({
            id: record.id,
            kind: record.kind,
            sequence: record.sequence,
            printedEntryNumber: record.printedEntryNumber,
            volume: record.volume,
            printedPageStart: 3,
            printedPageEnd: 3,
            sectionId,
            titleEn: record.title.en,
            titleAr: record.title.ar,
            translationState: record.translationState,
            machineAssessment: record.machineAssessment,
            humanReview: record.humanReview,
            unresolvedCount: 0,
          })),
        },
      ],
      [
        "/api/corpus/al-isabah/reviews",
        {
          corpusId,
          reviewedItems: 1,
          items: {
            [firstItem.id]: {
              approvalCount: 1,
              currentUserApproved: false,
              latestApprovalAt: 1_765_000_000,
            },
          },
        },
      ],
      [
        `/api/corpus/al-isabah/sections/${sectionId}`,
        {
          schemaVersion: "2.0.0",
          corpusId,
          id: sectionId,
          volume: 8,
          label: "Pages 1–25",
          availability: "complete_translation",
          position: 1,
          totalSections: 1,
          printedPageStart: 3,
          printedPageEnd: 3,
          previousSectionId: null,
          nextSectionId: null,
          items: [firstItem, untranslatedItem],
        },
      ],
    ]);

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const path = typeof input === "string" ? input : input.toString();
        const body = responses.get(path);
        return { ok: body !== undefined, json: async () => body };
      }),
    );

    render(<CorpusReader />);

    expect(
      await screen.findByRole("heading", { name: "Pages 1–25" }),
    ).toBeTruthy();
    expect(
      (screen.getByLabelText("Reading volume") as HTMLSelectElement).value,
    ).toBe("8");
    expect(screen.getByText("The first short translated record.")).toBeTruthy();
    expect(
      screen.getByText("English text is contained in the entry heading."),
    ).toBeTruthy();
    expect(
      screen.getByText(
        "This Arabic-only record has no translation to approve. Add or correct the translation through the review workspace first.",
      ),
    ).toBeTruthy();
    expect(
      screen.getAllByRole("button", { name: "Approve this translation" }),
    ).toHaveLength(1);
    expect(screen.getAllByText("Review record")).toHaveLength(2);
    expect(
      screen.getByText("Human reviewed · 1 current approval"),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Hide human-reviewed translations",
      }),
    );
    expect(screen.queryByText("The first short translated record.")).toBeNull();
    expect(
      screen.getByText("English text is contained in the entry heading."),
    ).toBeTruthy();
    expect(
      screen.getByText("Showing 1 of 2 records in this section"),
    ).toBeTruthy();
    await waitFor(() =>
      expect(
        document.querySelectorAll(".reading-record.short-record"),
      ).toHaveLength(1),
    );
    expect(document.body.textContent?.toLocaleLowerCase()).not.toContain(
      "khadijah",
    );
  });
});

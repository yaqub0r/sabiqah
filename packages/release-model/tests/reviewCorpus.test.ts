import { describe, expect, it } from "vitest";

import {
  parseReviewCorpusIndex,
  parseReviewCorpusItem,
  parseReviewCorpusSection,
  parseReviewCorpusSummary,
} from "../src/reviewCorpus";

const corpusId = "al-isabah-reading-a3b76bf-v3";
const item = {
  schemaVersion: "2.0.0" as const,
  corpusId,
  id: "isabah-entry-00010759",
  kind: "entry" as const,
  sequence: 10759,
  printedEntryNumber: 10759,
  volume: 8,
  title: { en: "Asiya bint al-Harith", ar: "آسية بنت الحارث" },
  headingsBefore: [
    {
      level: "section" as const,
      en: "Section One",
      ar: "القسم الأول",
      context: "continued" as const,
      contextSourceEntryNumber: 11425,
    },
  ],
  translationState: "translated" as const,
  machineAssessment: "passed" as const,
  humanReview: "unreviewed" as const,
  segments: [
    {
      id: "isabah-entry-00010759-segment-0001",
      arabic: "آسية بنت الحارث",
      english: "Asiya bint al-Harith.",
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
      stage: "machine_validation" as const,
      state: "complete" as const,
      summary: "Machine validation passed.",
    },
    {
      stage: "human_review" as const,
      state: "pending" as const,
      summary: "Human review has not started.",
    },
    {
      stage: "compliance_promotion" as const,
      state: "blocked" as const,
      summary: "Public promotion is blocked.",
    },
  ],
  provenance: {
    sourceArtifactId: "al-isabah:entry:10759",
    sourceArtifactSha256:
      "f12585cea28d7c7b318728f74b1a95a0d8b2812cb25d6e70f1b9e7b0b9422a3f",
  },
};

describe("review reading contract", () => {
  it("organizes a blocked corpus by book volumes", () => {
    const summary = parseReviewCorpusSummary({
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
        entries: 1565,
        passages: 14,
        translated: 1579,
        needsAttention: 215,
        unresolvedItems: 288,
        humanReviewed: 0,
      },
      exclusions: {
        contextualPassagesPendingPublicSourceAlignment: 14,
        recordsPendingRemediation: 0,
      },
      volumes: [
        {
          id: "volume-01",
          number: 1,
          label: "Volume 1",
          availability: "not_translated",
          sourceItemCount: 1536,
          itemCount: 0,
          sectionCount: 0,
          firstPrintedPage: null,
          lastPrintedPage: null,
          description: "No working translation yet.",
        },
        {
          id: "volume-08",
          number: 8,
          label: "Volume 8",
          availability: "complete_translation",
          sourceItemCount: 1550,
          itemCount: 1550,
          sectionCount: 20,
          firstPrintedPage: 3,
          lastPrintedPage: 492,
          description: "Complete working translation.",
        },
      ],
    });
    expect(summary.volumes[0]?.availability).toBe("not_translated");
    expect(summary.volumes[1]?.availability).toBe("complete_translation");
    expect(summary.volumes[1]?.sourceItemCount).toBe(1550);
    expect(
      summary.exclusions?.contextualPassagesPendingPublicSourceAlignment,
    ).toBe(14);
    expect(JSON.stringify(summary)).not.toContain("cohort");
  });

  it("rejects a corpus that claims promotion eligibility", () => {
    expect(() =>
      parseReviewCorpusSummary({
        schemaVersion: "2.0.0",
        work: { slug: "al-isabah", titleAr: "الإصابة", titleEn: "Al-Isabah" },
        corpus: {
          id: corpusId,
          sourceRepository: "https://github.com/yaqub0r/al-isabah",
          sourceCommit: "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178",
          generatedAt: "2026-08-12T00:00:00.000Z",
          promotionStatus: "eligible",
        },
        counts: {
          entries: 0,
          passages: 0,
          translated: 0,
          needsAttention: 0,
          unresolvedItems: 0,
          humanReviewed: 0,
        },
        volumes: [],
      }),
    ).toThrow();
  });

  it("rejects continued structure without its original source location", () => {
    expect(() =>
      parseReviewCorpusItem({
        ...item,
        headingsBefore: [
          {
            level: "section",
            en: "Section One",
            ar: "القسم الأول",
            context: "continued",
          },
        ],
      }),
    ).toThrow(/original source entry number/);
  });

  it("parses index, detail, and continuous section records", () => {
    const sectionId = "volume-08-pages-0001-0025";
    const index = parseReviewCorpusIndex({
      schemaVersion: "2.0.0",
      corpusId,
      items: [
        {
          id: item.id,
          kind: "entry",
          sequence: 10759,
          printedEntryNumber: 10759,
          volume: 8,
          printedPageStart: 3,
          printedPageEnd: 3,
          sectionId,
          titleEn: item.title.en,
          titleAr: item.title.ar,
          translationState: "translated",
          machineAssessment: "passed",
          humanReview: "unreviewed",
          unresolvedCount: 0,
        },
      ],
    });
    expect(index.items[0]?.sectionId).toBe(sectionId);
    const parsedItem = parseReviewCorpusItem(item);
    expect(parsedItem.segments[0]?.english).toContain("Asiya");
    expect(parsedItem.headingsBefore?.[0]?.context).toBe("continued");

    const section = parseReviewCorpusSection({
      schemaVersion: "2.0.0",
      corpusId,
      id: sectionId,
      volume: 8,
      label: "Pages 3–25",
      availability: "complete_translation",
      position: 1,
      totalSections: 20,
      printedPageStart: 3,
      printedPageEnd: 25,
      previousSectionId: null,
      nextSectionId: "volume-08-pages-0026-0050",
      items: [item],
    });
    expect(section.items).toHaveLength(1);
  });
});

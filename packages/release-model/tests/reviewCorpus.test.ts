import { describe, expect, it } from "vitest";

import {
  parseReviewCorpusIndex,
  parseReviewCorpusItem,
  parseReviewCorpusSummary,
} from "../src/reviewCorpus";

const corpusId = "al-isabah-review-a3b76bf";

describe("review corpus contract", () => {
  it("accepts a blocked corpus summary", () => {
    const summary = parseReviewCorpusSummary({
      schemaVersion: "1.0.0",
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
        contextualPassages: 14,
        translated: 1579,
        needsAttention: 214,
        unresolvedItems: 287,
        humanReviewed: 0,
      },
      collections: [
        {
          id: "volume-08",
          title: "Volume 8",
          kind: "volume",
          itemCount: 1550,
          reviewState: "unreviewed",
          description: "Translated entries awaiting review.",
        },
      ],
    });
    expect(summary.corpus.promotionStatus).toBe("blocked");
  });

  it("rejects a corpus summary that claims promotion eligibility", () => {
    expect(() =>
      parseReviewCorpusSummary({
        schemaVersion: "1.0.0",
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
          contextualPassages: 0,
          translated: 0,
          needsAttention: 0,
          unresolvedItems: 0,
          humanReviewed: 0,
        },
        collections: [],
      }),
    ).toThrow();
  });

  it("parses list and detail records separately", () => {
    const index = parseReviewCorpusIndex({
      schemaVersion: "1.0.0",
      corpusId,
      items: [
        {
          id: "isabah-entry-00010759",
          kind: "entry",
          sequence: 10759,
          printedEntryNumber: 10759,
          volume: "8",
          titleEn: "Asiya bint al-Harith",
          titleAr: "آسية بنت الحارث",
          translationState: "translated",
          machineAssessment: "passed",
          humanReview: "unreviewed",
          unresolvedCount: 0,
          collectionIds: ["volume-08"],
        },
      ],
    });
    expect(index.items).toHaveLength(1);

    const item = parseReviewCorpusItem({
      schemaVersion: "1.0.0",
      corpusId,
      id: "isabah-entry-00010759",
      kind: "entry",
      sequence: 10759,
      printedEntryNumber: 10759,
      volume: "8",
      title: { en: "Asiya bint al-Harith", ar: "آسية بنت الحارث" },
      translationState: "translated",
      machineAssessment: "passed",
      humanReview: "unreviewed",
      collectionIds: ["volume-08"],
      segments: [
        {
          id: "isabah-entry-00010759-segment-0001",
          arabic: "آسية بنت الحارث",
          english: "Asiya bint al-Harith",
          pages: [
            {
              volume: "8",
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
        {
          stage: "human_review",
          state: "pending",
          summary: "Human review has not started.",
        },
        {
          stage: "compliance_promotion",
          state: "blocked",
          summary: "Public promotion is blocked.",
        },
      ],
      provenance: {
        sourceArtifactId: "firstlight:volume-08",
        sourceArtifactSha256:
          "f12585cea28d7c7b318728f74b1a95a0d8b2812cb25d6e70f1b9e7b0b9422a3f",
      },
    });
    expect(item.segments[0]?.english).toContain("Asiya");
  });
});

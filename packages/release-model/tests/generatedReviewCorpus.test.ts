// @ts-nocheck -- Node built-ins are available to Vitest, but this browser-shared
// package intentionally does not expose Node ambient types to its source model.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  parseReviewCorpusIndex,
  parseReviewCorpusItem,
  parseReviewCorpusSection,
  parseReviewCorpusSummary,
} from "../src/reviewCorpus";

const corpusRoot = process.env.REVIEW_CORPUS_PATH;

describe.skipIf(!corpusRoot)("generated review corpus", () => {
  it("matches the runtime schemas in full", () => {
    const load = (relative: string): unknown =>
      JSON.parse(readFileSync(resolve(corpusRoot!, relative), "utf8"));
    const summary = parseReviewCorpusSummary(load("summary.json"));
    const index = parseReviewCorpusIndex(load("index.json"));

    expect(summary.schemaVersion).toBe("4.0.0");
    expect(summary.corpus.publicationStatus).toBe("public-working");
    expect(summary.corpus.sourceAuthorityId).toBe(
      "al-isabah-openiti-5835c18-aco-v1",
    );
    expect(summary.corpus.license?.spdx).toBe("CC-BY-NC-SA-4.0");
    expect(summary.counts.sourceInventory).toBe(
      summary.counts.entries +
        summary.counts.passages +
        (summary.counts.quarantined ?? 0),
    );
    expect(index.corpusId).toBe(summary.corpus.id);
    expect(index.items).toHaveLength(
      summary.counts.entries + summary.counts.passages,
    );
    expect(summary.counts.translated).toBe(
      summary.counts.entries + summary.counts.passages,
    );
    for (const listed of index.items) {
      const item = parseReviewCorpusItem(load(`items/${listed.id}.json`));
      expect(item.id).toBe(listed.id);
      expect(item.corpusId).toBe(index.corpusId);
      expect(item.publicEligibility).toBe("eligible");
      expect(item.source?.authorityId).toBe(summary.corpus.sourceAuthorityId);
      if (item.remediation) {
        expect(item.remediation.sourceArabicReplaced).toBe(true);
        expect(item.remediation.privateLocatorsRemoved).toBe(true);
        expect(item.remediation.englishExcluded).toBe(false);
      } else {
        expect(item.source?.alignment.method).toBe(
          "al-isabah-public-distribution-v1",
        );
      }
      if (item.remediation?.sourcePresentationRepairs !== undefined) {
        expect(
          item.remediation.sourcePresentationRepairs,
        ).toBeGreaterThanOrEqual(0);
      }
      expect(item.honorificPolicyVersion).toBe("1.0.0");
      expect(item.honorifics).toBeDefined();
      expect(JSON.stringify(item).toLocaleLowerCase()).not.toContain("usul.ai");
    }
    const sectionIds = new Set(index.items.map((item) => item.sectionId));
    const sectionItems: string[] = [];
    for (const sectionId of sectionIds) {
      const section = parseReviewCorpusSection(
        load(`sections/${sectionId}.json`),
      );
      sectionItems.push(...section.items.map((item) => item.id));
    }
    expect(sectionItems.sort()).toEqual(
      index.items.map((item) => item.id).sort(),
    );
    expect(JSON.stringify(summary).toLocaleLowerCase()).not.toContain(
      "khadijah",
    );
  });

  it("rejects a negative source presentation repair count", () => {
    const index = parseReviewCorpusIndex(
      JSON.parse(readFileSync(resolve(corpusRoot!, "index.json"), "utf8")),
    );
    const first = JSON.parse(
      readFileSync(
        resolve(corpusRoot!, `items/${index.items[0]!.id}.json`),
        "utf8",
      ),
    );
    first.remediation = {
      legacyAllocationNumber: 1,
      sourceArabicReplaced: true,
      privateLocatorsRemoved: true,
      honorificInventory: {},
      honorificTypeCorrections: 0,
      removedApparatusParagraphs: 0,
      removedEditorialNotes: 0,
      sourcePresentationRepairs: -1,
    };
    expect(() => parseReviewCorpusItem(first)).toThrow();
  });
});

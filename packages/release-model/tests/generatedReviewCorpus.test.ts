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

    expect(["4.0.0", "5.0.0"]).toContain(summary.schemaVersion);
    expect(index.schemaVersion).toBe(summary.schemaVersion);
    expect(summary.corpus.publicationStatus).toBe("public-working");
    const cohorts =
      summary.schemaVersion === "5.0.0" && "cohorts" in summary.corpus
        ? summary.corpus.cohorts
        : [];
    const cohortById = new Map(cohorts.map((cohort) => [cohort.id, cohort]));
    const cohortItemIds = new Map(
      cohorts.map((cohort) => [cohort.id, new Set(cohort.membership.itemIds)]),
    );
    if (summary.schemaVersion === "5.0.0") {
      expect(cohorts).not.toHaveLength(0);
      expect(
        cohorts.flatMap((cohort) => cohort.membership.itemIds).sort(),
      ).toEqual(index.items.map((item) => item.id).sort());
      for (const cohort of cohorts) {
        expect(cohort.rights.arabicSource.license.spdx).toBe("CC-BY-NC-SA-4.0");
        expect(cohort.rights.englishTranslation.license.spdx).toBe(
          "CC-BY-NC-SA-4.0",
        );
      }
    } else {
      expect(summary.corpus.sourceAuthorityId).toBe(
        "al-isabah-openiti-5835c18-aco-v1",
      );
      expect(summary.corpus.license?.spdx).toBe("CC-BY-NC-SA-4.0");
    }
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
      expect(item.schemaVersion).toBe(summary.schemaVersion);
      expect(item.id).toBe(listed.id);
      expect(item.corpusId).toBe(index.corpusId);
      expect(item.cohortId).toBe(listed.cohortId);
      expect(item.publicEligibility).toBe("eligible");
      const cohort = item.cohortId ? cohortById.get(item.cohortId) : undefined;
      if (summary.schemaVersion === "5.0.0") {
        expect(cohort).toBeDefined();
        expect(cohortItemIds.get(item.cohortId)?.has(item.id)).toBe(true);
        expect(item.source?.authorityId).toBe(cohort?.source.authorityId);
        expect(item.source?.sourceRepository).toBe(cohort?.source.repository);
        expect(item.source?.sourceCommit).toBe(cohort?.source.commit);
        expect(item.source?.sourceArtifactSha256).toBe(
          cohort?.source.artifactSha256,
        );
        expect(item.source?.license).toEqual(
          cohort?.rights.arabicSource.license,
        );
        expect(item.source?.englishRights).toEqual(
          cohort?.rights.englishTranslation,
        );
        expect(item.source?.rightsMatrix).toEqual(cohort?.rights.matrix);
      } else {
        expect(item.source?.authorityId).toBe(summary.corpus.sourceAuthorityId);
      }
      if (item.remediation) {
        expect(item.remediation.sourceArabicReplaced).toBe(true);
        expect(item.remediation.privateLocatorsRemoved).toBe(true);
        expect(item.remediation.englishExcluded).toBe(false);
      } else {
        expect(item.source?.alignment.method).toBe(
          cohort?.kind === "distribution-v2"
            ? "al-isabah-public-distribution-v2"
            : "al-isabah-public-distribution-v1",
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
      expect(section.schemaVersion).toBe(summary.schemaVersion);
      expect(section.corpusId).toBe(index.corpusId);
      sectionItems.push(...section.items.map((item) => item.id));
    }
    expect(sectionItems.sort()).toEqual(
      index.items.map((item) => item.id).sort(),
    );
    expect(JSON.stringify(summary).toLocaleLowerCase()).not.toContain(
      "khadijah",
    );
  }, 30_000);

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

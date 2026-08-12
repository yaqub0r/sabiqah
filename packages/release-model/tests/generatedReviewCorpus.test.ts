// @ts-nocheck -- Node built-ins are available to Vitest, but this browser-shared
// package intentionally does not expose Node ambient types to its source model.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  parseReviewCorpusIndex,
  parseReviewCorpusItem,
  parseReviewCorpusSummary,
} from "../src/reviewCorpus";

const corpusRoot = process.env.REVIEW_CORPUS_PATH;

describe.skipIf(!corpusRoot)("generated review corpus", () => {
  it("matches the runtime schemas in full", () => {
    const load = (relative: string): unknown =>
      JSON.parse(readFileSync(resolve(corpusRoot!, relative), "utf8"));
    const summary = parseReviewCorpusSummary(load("summary.json"));
    const index = parseReviewCorpusIndex(load("index.json"));

    expect(index.corpusId).toBe(summary.corpus.id);
    expect(index.items).toHaveLength(
      summary.counts.entries + summary.counts.contextualPassages,
    );
    for (const listed of index.items) {
      const item = parseReviewCorpusItem(load(`items/${listed.id}.json`));
      expect(item.id).toBe(listed.id);
      expect(item.corpusId).toBe(index.corpusId);
    }
  });
});

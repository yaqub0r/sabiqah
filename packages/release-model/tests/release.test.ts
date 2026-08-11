import { describe, expect, it } from "vitest";

import fixture from "../../../fixtures/releases/al-isabah-beta-v1.json";
import { bookReleaseSchema, reviewProposalSchema } from "../src/index";

describe("book release contract", () => {
  it("accepts the three representative beta entries", () => {
    const release = bookReleaseSchema.parse(fixture);
    expect(release.entries).toHaveLength(3);
    expect(release.entries.some((entry) => entry.issues.length > 0)).toBe(true);
  });

  it("rejects an Arabic correction without evidence", () => {
    const result = reviewProposalSchema.safeParse({
      proposalVersion: "1.0.0",
      bookSlug: "al-isabah",
      baseReleaseId: "fixture-beta-v1",
      entryId: "isabah-fixture-0003",
      createdAt: "2026-08-11T12:00:00.000Z",
      operations: [
        {
          segmentId: "isabah-fixture-0003-segment-0001",
          target: "canonical_arabic",
          proposedText: "نص مصحح",
          rationale: "guess",
          evidenceRefs: [],
        },
      ],
    });

    expect(result.success).toBe(false);
  });
});

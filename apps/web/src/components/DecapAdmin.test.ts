import { describe, expect, it } from "vitest";
import { parsePendingProposal } from "./DecapAdmin";

describe("parsePendingProposal", () => {
  it("returns one plain operation for one prepared operation", () => {
    const proposal = parsePendingProposal(
      JSON.stringify({
        proposalVersion: "1.0.0",
        operations: [{ segmentId: "segment-1", target: "translation" }],
      }),
    );

    expect(proposal).toEqual({
      proposalVersion: "1.0.0",
      operations: [{ segmentId: "segment-1", target: "translation" }],
    });
    expect(Object.getPrototypeOf(proposal)).toBe(Object.prototype);
  });
});

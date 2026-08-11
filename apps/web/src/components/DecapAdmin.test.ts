import { describe, expect, it } from "vitest";
import { parsePendingProposal, proposalFormat } from "./DecapAdmin";

describe("parsePendingProposal", () => {
  it("keeps nested lists out of Decap's editor state", () => {
    const pending = JSON.stringify({
      proposalVersion: "1.0.0",
      operations: [{ segmentId: "segment-1", target: "translation" }],
    });

    expect(parsePendingProposal(pending)).toBe(pending);
  });
});

describe("proposalFormat", () => {
  it("round-trips one prepared operation as one repository operation", () => {
    const file = JSON.stringify({
      proposal: {
        proposalVersion: "1.0.0",
        operations: [{ segmentId: "segment-1", target: "translation" }],
      },
    });

    const editorValue = proposalFormat.fromFile(file);
    expect(typeof editorValue.proposal).toBe("string");

    const saved = JSON.parse(proposalFormat.toFile(editorValue));
    expect(saved.proposal.operations).toHaveLength(1);
    expect(saved).toEqual(JSON.parse(file));
  });
});

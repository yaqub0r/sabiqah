// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CorpusItemReview } from "./CorpusItemReview";

const itemId = "isabah-entry-00010759";
const corpusId = "al-isabah-reading-a3b76bf-v2";
const reviewItem = {
  schemaVersion: "2.0.0",
  corpusId,
  id: itemId,
  kind: "entry",
  sequence: 10_759,
  printedEntryNumber: 10_759,
  volume: 8,
  title: { en: "A translated entry", ar: "اسم" },
  translationState: "translated",
  machineAssessment: "passed",
  humanReview: "unreviewed",
  segments: [
    {
      id: `${itemId}-segment-1`,
      arabic: "نص عربي.",
      english: "An English translation.",
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
    sourceArtifactId: "al-isabah:entry:10759",
    sourceArtifactSha256:
      "f12585cea28d7c7b318728f74b1a95a0d8b2812cb25d6e70f1b9e7b0b9422a3f",
  },
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

describe("CorpusItemReview", () => {
  it("shows the current approval and decision control", async () => {
    window.history.replaceState(
      null,
      "",
      `/works/al-isabah/review/?id=${itemId}`,
    );
    const responses = new Map<string, unknown>([
      [
        "/api/session",
        { identity: { login: "reader", membershipStatus: "active" } },
      ],
      [`/api/corpus/al-isabah/items/${itemId}`, reviewItem],
      [
        "/api/corpus/al-isabah/reviews",
        {
          corpusId,
          reviewedItems: 1,
          items: {
            [itemId]: {
              approvalCount: 1,
              currentUserApproved: true,
              latestApprovalAt: 1_765_000_000,
            },
          },
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

    render(<CorpusItemReview />);

    expect(
      await screen.findByRole("button", { name: "Withdraw my approval" }),
    ).toBeTruthy();
    expect(
      screen.getByText("Human reviewed · 1 current approval"),
    ).toBeTruthy();
  });
});

describe("CorpusItemReview Arabic-only records", () => {
  it("does not offer approval when no translation exists", async () => {
    window.history.replaceState(
      null,
      "",
      `/works/al-isabah/review/?id=${itemId}`,
    );
    const untranslatedItem = {
      ...reviewItem,
      title: { ...reviewItem.title, en: "Entry 10759" },
      translationState: "untranslated",
      segments: reviewItem.segments.map((segment) => ({
        ...segment,
        english: "",
      })),
    };
    const responses = new Map<string, unknown>([
      [
        "/api/session",
        { identity: { login: "reader", membershipStatus: "active" } },
      ],
      [`/api/corpus/al-isabah/items/${itemId}`, untranslatedItem],
      [
        "/api/corpus/al-isabah/reviews",
        { corpusId, reviewedItems: 0, items: {} },
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

    render(<CorpusItemReview />);

    expect(
      await screen.findByText(
        "This Arabic-only record has no translation to approve. Add or correct the translation before submitting an approval.",
      ),
    ).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Approve this translation" }),
    ).toBeNull();
  });
});

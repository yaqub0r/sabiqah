import { describe, expect, it, vi } from "vitest";

import { LEGACY_CORPUS_CONTEXT, corpusObjectKey } from "./corpus";
import {
  createSelectionReport,
  parseSelectionReport,
} from "./selectionReports";

const item = {
  corpusId: LEGACY_CORPUS_CONTEXT.id,
  id: "isabah-entry-00011452",
  printedEntryNumber: 11452,
  title: { en: "A title", ar: "عنوان" },
  segments: [
    {
      id: "isabah-entry-00011452-segment-1",
      arabic: "هذا نص عربي للاختبار.",
      english: "This is public translated text for testing.",
      pages: [{ printedPage: 11 }],
    },
  ],
};

const valid = {
  corpusId: LEGACY_CORPUS_CONTEXT.id,
  itemId: item.id,
  segmentId: item.segments[0]!.id,
  field: "segment",
  language: "English",
  category: "translation",
  selectedText: "public translated text",
  context: "This is public translated text for testing.",
  comment: "The wording needs another look.",
  pageUrl: `/works/al-isabah/?volume=8#${item.id}`,
};

function bucketFor(value: unknown): R2Bucket {
  return {
    get: vi.fn(async (key: string) => {
      expect(key).toBe(corpusObjectKey(LEGACY_CORPUS_CONTEXT, "item", item.id));
      return { json: async () => value };
    }),
  } as unknown as R2Bucket;
}

describe("selection reports", () => {
  it("parses only current, bounded report payloads", () => {
    expect(parseSelectionReport(valid)).toMatchObject({
      category: "translation",
      itemId: item.id,
    });
    expect(parseSelectionReport({ ...valid, corpusId: "stale" })).toBeNull();
    expect(
      parseSelectionReport({ ...valid, selectedText: "x".repeat(1_001) }),
    ).toBeNull();
    expect(parseSelectionReport({ ...valid, category: "anything" })).toBeNull();
  });

  it("creates an escaped, structured issue from canonical corpus data", async () => {
    const githubFetch = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) => {
        const request = JSON.parse(String(init?.body)) as {
          title: string;
          body: string;
        };
        expect(request.title).toBe("[translation] Al-Isabah entry 11452");
        expect(request.body).toContain("Printed page:** 11");
        expect(request.body).toContain(`<code>${item.segments[0]!.id}</code>`);
        expect(request.body).toContain("@beta-reviewer");
        expect(request.body).toContain("&lt;script&gt;");
        expect(request.body).not.toContain("<script>");
        return new Response(
          JSON.stringify({
            number: 91,
            html_url: "https://github.com/yaqub0r/sabiqah/issues/91",
          }),
          { status: 201 },
        );
      },
    );
    const result = await createSelectionReport(
      bucketFor(item),
      LEGACY_CORPUS_CONTEXT,
      "server-secret",
      { github_login: "beta-reviewer" },
      { ...valid, comment: "Check <script>alert(1)</script>" },
      "https://dev.sabiqah.org/api/corpus/al-isabah/reports",
      githubFetch,
    );
    expect(result.number).toBe(91);
    const headers = githubFetch.mock.calls[0]![1]!.headers as Record<
      string,
      string
    >;
    expect(headers.authorization).toBe("Bearer server-secret");
  });

  it("validates context against the accessible honorific rendering", async () => {
    const honorificItem = {
      ...item,
      segments: [
        {
          ...item.segments[0]!,
          english:
            "The sister of Khadijah, the wife of the Prophet ﷺ.\n\nAl-Zubayr ibn Bakkar mentioned her.",
        },
      ],
    };
    const githubFetch = vi.fn(async () =>
      Response.json(
        {
          number: 98,
          html_url: "https://github.com/yaqub0r/sabiqah/issues/98",
        },
        { status: 201 },
      ),
    );

    await expect(
      createSelectionReport(
        bucketFor(honorificItem),
        LEGACY_CORPUS_CONTEXT,
        "server-secret",
        { github_login: "beta-reviewer" },
        {
          ...valid,
          selectedText: "The sister of Khadijah, the wife of the Prophet",
          context:
            "The sister of Khadijah, the wife of the Prophet may Allah bless him and grant him peace. Al-Zubayr ibn Bakkar mentioned her.",
        },
        "https://dev.sabiqah.org/api/corpus/al-isabah/reports",
        githubFetch,
      ),
    ).resolves.toEqual({
      number: 98,
      url: "https://github.com/yaqub0r/sabiqah/issues/98",
    });
  });

  it.each([
    [undefined, valid, 503],
    ["token", { ...valid, selectedText: "invented text" }, 409],
    [
      "token",
      { ...valid, pageUrl: "https://attacker.example/works/al-isabah/" },
      400,
    ],
  ])(
    "fails closed for missing config, stale text, and foreign URLs",
    async (token, payload, status) => {
      await expect(
        createSelectionReport(
          bucketFor(item),
          LEGACY_CORPUS_CONTEXT,
          token,
          { github_login: "beta-reviewer" },
          payload,
          "https://dev.sabiqah.org/api/corpus/al-isabah/reports",
        ),
      ).rejects.toMatchObject({ status });
    },
  );
});

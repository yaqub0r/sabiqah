import { describe, expect, it } from "vitest";

import { canReadCorpus, corpusJson, corpusObjectKey } from "../src/corpus";

describe("private review corpus", () => {
  it("requires an active member for corpus text", () => {
    expect(canReadCorpus(null)).toBe(false);
    expect(canReadCorpus({ status: "limited" })).toBe(false);
    expect(canReadCorpus({ status: "suspended" })).toBe(false);
    expect(canReadCorpus({ status: "active" })).toBe(true);
  });

  it("builds only pinned, sanitized object keys", () => {
    expect(corpusObjectKey("summary")).toContain("al-isabah-review-a3b76bf");
    expect(corpusObjectKey("item", "isabah-entry-00010759")).toMatch(
      /items\/isabah-entry-00010759\.json$/,
    );
    expect(() => corpusObjectKey("item", "../source.pdf")).toThrow(
      "Invalid corpus item ID",
    );
  });

  it("returns corpus JSON with private no-store caching", async () => {
    const bucket = {
      get: async () => ({ body: JSON.stringify({ ok: true }) }),
    } as unknown as R2Bucket;
    const response = await corpusJson(bucket, corpusObjectKey("summary"));
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.json()).toEqual({ ok: true });
  });

  it("fails closed when the pinned corpus is absent", async () => {
    const bucket = { get: async () => null } as unknown as R2Bucket;
    const response = await corpusJson(bucket, corpusObjectKey("summary"));
    expect(response.status).toBe(503);
  });
});

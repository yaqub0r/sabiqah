import { describe, expect, it } from "vitest";

import { canReviewCorpus, corpusJson, corpusObjectKey } from "../src/corpus";

describe("public working corpus", () => {
  it("requires an active member only for review actions", () => {
    expect(canReviewCorpus(null)).toBe(false);
    expect(canReviewCorpus({ status: "limited" })).toBe(false);
    expect(canReviewCorpus({ status: "suspended" })).toBe(false);
    expect(canReviewCorpus({ status: "active" })).toBe(true);
  });

  it("builds only pinned, sanitized object keys", () => {
    expect(corpusObjectKey("summary")).toContain(
      "al-isabah-public-openiti-5835c18-v4",
    );
    expect(corpusObjectKey("exclusions")).toMatch(/\/exclusions\.json$/);
    expect(corpusObjectKey("item", "isabah-entry-00010759")).toMatch(
      /items\/isabah-entry-00010759\.json$/,
    );
    expect(() => corpusObjectKey("item", "../source.pdf")).toThrow(
      "Invalid corpus item ID",
    );
    expect(corpusObjectKey("section", "volume-08-pages-0001-0025")).toMatch(
      /sections\/volume-08-pages-0001-0025\.json$/,
    );
    expect(() => corpusObjectKey("section", "../index")).toThrow(
      "Invalid corpus section ID",
    );
  });

  it("returns public corpus JSON with bounded shared caching", async () => {
    const bucket = {
      get: async () => ({ body: JSON.stringify({ ok: true }) }),
    } as unknown as R2Bucket;
    const response = await corpusJson(bucket, corpusObjectKey("summary"));
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe(
      "public, max-age=300, s-maxage=3600",
    );
    expect(await response.json()).toEqual({ ok: true });
  });

  it("fails closed when the pinned corpus is absent", async () => {
    const bucket = { get: async () => null } as unknown as R2Bucket;
    const response = await corpusJson(bucket, corpusObjectKey("summary"));
    expect(response.status).toBe(503);
  });
});

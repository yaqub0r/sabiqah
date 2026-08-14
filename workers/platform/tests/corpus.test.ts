import { describe, expect, it } from "vitest";

import {
  canReviewCorpus,
  CORPUS_POINTER_KEY,
  LEGACY_CORPUS_CONTEXT,
  corpusJson,
  corpusObjectKey,
  resolveCorpusContext,
} from "../src/corpus";

describe("public working corpus", () => {
  it("requires an active member only for review actions", () => {
    expect(canReviewCorpus(null)).toBe(false);
    expect(canReviewCorpus({ status: "limited" })).toBe(false);
    expect(canReviewCorpus({ status: "suspended" })).toBe(false);
    expect(canReviewCorpus({ status: "active" })).toBe(true);
  });

  it("builds only pinned, sanitized object keys", () => {
    expect(LEGACY_CORPUS_CONTEXT.id).toBe(
      "al-isabah-public-openiti-5835c18-v11",
    );
    expect(corpusObjectKey(LEGACY_CORPUS_CONTEXT, "summary")).toContain(
      LEGACY_CORPUS_CONTEXT.id,
    );
    expect(corpusObjectKey(LEGACY_CORPUS_CONTEXT, "exclusions")).toMatch(
      /\/exclusions\.json$/,
    );
    expect(
      corpusObjectKey(LEGACY_CORPUS_CONTEXT, "item", "isabah-entry-00010759"),
    ).toMatch(/items\/isabah-entry-00010759\.json$/);
    expect(() =>
      corpusObjectKey(LEGACY_CORPUS_CONTEXT, "item", "../source.pdf"),
    ).toThrow("Invalid corpus item ID");
    expect(
      corpusObjectKey(
        LEGACY_CORPUS_CONTEXT,
        "section",
        "volume-08-pages-0001-0025",
      ),
    ).toMatch(/sections\/volume-08-pages-0001-0025\.json$/);
    expect(() =>
      corpusObjectKey(LEGACY_CORPUS_CONTEXT, "section", "../index"),
    ).toThrow("Invalid corpus section ID");
  });

  it("resolves a validated mutable pointer to an immutable corpus prefix", async () => {
    const active = {
      schemaVersion: "1.0.0",
      corpusId: "al-isabah-public-openiti-5835c18-book-aaaaaaaaaaaa",
      prefix:
        "public-corpora/al-isabah/al-isabah-public-openiti-5835c18-book-aaaaaaaaaaaa",
    };
    const bucket = {
      get: async (key: string) => ({
        text: async () => {
          expect(key).toBe(CORPUS_POINTER_KEY);
          return JSON.stringify(active);
        },
      }),
    } as unknown as R2Bucket;
    await expect(resolveCorpusContext(bucket)).resolves.toEqual({
      id: active.corpusId,
      prefix: active.prefix,
    });
  });

  it("uses the legacy immutable corpus only when no pointer exists", async () => {
    const bucket = { get: async () => null } as unknown as R2Bucket;
    await expect(resolveCorpusContext(bucket)).resolves.toEqual(
      LEGACY_CORPUS_CONTEXT,
    );
  });

  it("returns public corpus JSON with bounded shared caching", async () => {
    const bucket = {
      get: async () => ({ body: JSON.stringify({ ok: true }) }),
    } as unknown as R2Bucket;
    const response = await corpusJson(
      bucket,
      corpusObjectKey(LEGACY_CORPUS_CONTEXT, "summary"),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe(
      "public, max-age=300, s-maxage=3600",
    );
    expect(await response.json()).toEqual({ ok: true });
  });

  it("fails closed when the pinned corpus is absent", async () => {
    const bucket = { get: async () => null } as unknown as R2Bucket;
    const response = await corpusJson(
      bucket,
      corpusObjectKey(LEGACY_CORPUS_CONTEXT, "summary"),
    );
    expect(response.status).toBe(503);
  });
});

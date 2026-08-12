import { describe, expect, it, vi } from "vitest";

import { CORPUS_ID } from "../src/corpus";
import {
  isSameOrigin,
  parseTranslationReviewAction,
  recordTranslationReview,
} from "../src/translationReviews";

const itemId = "isabah-entry-00010759";
const serializedItem = JSON.stringify({
  corpusId: CORPUS_ID,
  id: itemId,
  segments: [{ english: "Approved translation." }],
});

describe("translation reviews", () => {
  it("accepts only explicit review actions from the same origin", () => {
    expect(parseTranslationReviewAction({ action: "approve" })).toBe("approve");
    expect(parseTranslationReviewAction({ action: "withdraw" })).toBe(
      "withdraw",
    );
    expect(parseTranslationReviewAction({ action: "publish" })).toBeNull();
    expect(
      isSameOrigin(
        new Request(`https://dev.sabiqah.org/api/reviews/${itemId}`, {
          headers: { origin: "https://dev.sabiqah.org" },
        }),
      ),
    ).toBe(true);
    expect(
      isSameOrigin(
        new Request(`https://dev.sabiqah.org/api/reviews/${itemId}`, {
          headers: { origin: "https://attacker.example" },
        }),
      ),
    ).toBe(false);
  });

  it("records approval against the exact private corpus object", async () => {
    let inserted: unknown[] | undefined;
    const prepare = vi.fn((sql: string) => ({
      bind: (...values: unknown[]) => ({
        first: async () => null,
        run: async () => {
          if (sql.includes("INSERT INTO translation_review_events")) {
            inserted = values;
          }
          return { success: true };
        },
        all: async () => ({
          results: [
            {
              item_id: itemId,
              approval_count: 1,
              current_user_approved: 1,
              latest_approval_at: 1_765_000_000,
            },
          ],
        }),
      }),
    }));
    const db = { prepare } as unknown as D1Database;
    const bucket = {
      get: async () => ({ text: async () => serializedItem }),
    } as unknown as R2Bucket;

    const state = await recordTranslationReview(
      db,
      bucket,
      7,
      itemId,
      "approve",
    );

    expect(state).toEqual({
      approvalCount: 1,
      currentUserApproved: true,
      latestApprovalAt: 1_765_000_000,
    });
    expect(inserted?.slice(0, 4)).toEqual([7, CORPUS_ID, itemId, "approve"]);
    expect(inserted?.[4]).toMatch(/^[a-f0-9]{64}$/);
    expect(inserted?.slice(5)).toEqual([CORPUS_ID, itemId, 7, "approve"]);
  });

  it("uses one conditional insert to make repeated decisions idempotent", async () => {
    let insertSql = "";
    let insertValues: unknown[] = [];
    const prepare = vi.fn((sql: string) => ({
      bind: (...values: unknown[]) => ({
        run: async () => {
          if (sql.includes("INSERT INTO translation_review_events")) {
            insertSql = sql;
            insertValues = values;
          }
          return { success: true };
        },
        all: async () => ({
          results: [
            {
              item_id: itemId,
              approval_count: 1,
              current_user_approved: 1,
              latest_approval_at: 1_765_000_000,
            },
          ],
        }),
      }),
    }));
    const bucket = {
      get: async () => ({ text: async () => serializedItem }),
    } as unknown as R2Bucket;

    await recordTranslationReview(
      { prepare } as unknown as D1Database,
      bucket,
      7,
      itemId,
      "approve",
    );

    expect(insertSql).toContain("WHERE COALESCE");
    expect(insertSql).toContain("ORDER BY id DESC LIMIT 1");
    expect(insertValues.at(-1)).toBe("approve");
  });

  it("refuses to approve an item missing from the pinned corpus", async () => {
    const state = await recordTranslationReview(
      { prepare: vi.fn() } as unknown as D1Database,
      { get: async () => null } as unknown as R2Bucket,
      7,
      itemId,
      "approve",
    );
    expect(state).toBeNull();
  });
});

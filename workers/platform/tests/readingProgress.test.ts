import { describe, expect, it, vi } from "vitest";

import { CORPUS_ID } from "../src/corpus";
import {
  getTranslationReadSummary,
  setTranslationReadState,
} from "../src/readingProgress";

const itemId = "isabah-entry-00010759";
const serializedItem = JSON.stringify({
  corpusId: CORPUS_ID,
  id: itemId,
  segments: [{ english: "A public working translation." }],
});

describe("translation reading progress", () => {
  it("returns only the current member's private progress", async () => {
    let bindings: unknown[] = [];
    const db = {
      prepare: vi.fn(() => ({
        bind: (...values: unknown[]) => {
          bindings = values;
          return {
            all: async () => ({
              results: [{ item_id: itemId, read_at: 1_765_000_000 }],
            }),
          };
        },
      })),
    } as unknown as D1Database;

    await expect(getTranslationReadSummary(db, 7)).resolves.toEqual({
      corpusId: CORPUS_ID,
      readItems: 1,
      items: { [itemId]: { readAt: 1_765_000_000 } },
    });
    expect(bindings).toEqual([7, CORPUS_ID]);
  });

  it("marks and unmarks an exact translated corpus item", async () => {
    const operations: Array<{ sql: string; values: unknown[] }> = [];
    const db = {
      prepare: vi.fn((sql: string) => ({
        bind: (...values: unknown[]) => ({
          first: async () => {
            operations.push({ sql, values });
            return { read_at: 1_765_000_001 };
          },
          run: async () => {
            operations.push({ sql, values });
            return { success: true };
          },
        }),
      })),
    } as unknown as D1Database;
    const bucket = {
      get: async () => ({ text: async () => serializedItem }),
    } as unknown as R2Bucket;

    await expect(
      setTranslationReadState(db, bucket, 7, itemId, true),
    ).resolves.toEqual({
      found: true,
      state: { readAt: 1_765_000_001 },
    });
    await expect(
      setTranslationReadState(db, bucket, 7, itemId, false),
    ).resolves.toEqual({ found: true, state: null });

    expect(operations[0]?.sql).toContain("ON CONFLICT");
    expect(operations[0]?.values).toEqual([7, CORPUS_ID, itemId]);
    expect(operations[1]?.sql).toContain("DELETE FROM");
    expect(operations[1]?.values).toEqual([7, CORPUS_ID, itemId]);
  });

  it("does not store progress for an unknown corpus item", async () => {
    const db = { prepare: vi.fn() } as unknown as D1Database;
    await expect(
      setTranslationReadState(
        db,
        { get: async () => null } as unknown as R2Bucket,
        7,
        itemId,
        true,
      ),
    ).resolves.toEqual({ found: false, state: null });
    expect(db.prepare).not.toHaveBeenCalled();
  });
});

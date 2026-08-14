import { type CorpusContext, corpusObjectKey } from "./corpus";

export interface TranslationReadState {
  readAt: number;
}

export interface TranslationReadSummary {
  corpusId: string;
  readItems: number;
  items: Record<string, TranslationReadState>;
}

interface ReadRow {
  item_id: string;
  read_at: number;
}

interface CorpusReadItem {
  corpusId: string;
  id: string;
  segments: Array<{ english: string }>;
}

export async function getTranslationReadSummary(
  db: D1Database,
  memberId: number,
  corpusId: string,
): Promise<TranslationReadSummary> {
  const result = await db
    .prepare(
      `SELECT item_id, read_at
       FROM translation_read_progress
       WHERE member_id = ? AND corpus_id = ?`,
    )
    .bind(memberId, corpusId)
    .all<ReadRow>();
  const items = Object.fromEntries(
    result.results.map((row) => [row.item_id, { readAt: Number(row.read_at) }]),
  );
  return { corpusId, readItems: result.results.length, items };
}

export async function setTranslationReadState(
  db: D1Database,
  bucket: R2Bucket,
  corpus: CorpusContext,
  memberId: number,
  itemId: string,
  read: boolean,
): Promise<{ found: boolean; state: TranslationReadState | null }> {
  const object = await bucket.get(corpusObjectKey(corpus, "item", itemId));
  if (!object) return { found: false, state: null };
  const item = JSON.parse(await object.text()) as Partial<CorpusReadItem>;
  if (
    item.corpusId !== corpus.id ||
    item.id !== itemId ||
    !Array.isArray(item.segments) ||
    !item.segments.some(
      (segment) =>
        typeof segment?.english === "string" && segment.english.trim() !== "",
    )
  ) {
    throw new Error("Corpus reading item is inconsistent");
  }

  if (!read) {
    await db
      .prepare(
        `DELETE FROM translation_read_progress
         WHERE member_id = ? AND corpus_id = ? AND item_id = ?`,
      )
      .bind(memberId, corpus.id, itemId)
      .run();
    return { found: true, state: null };
  }

  const row = await db
    .prepare(
      `INSERT INTO translation_read_progress
        (member_id, corpus_id, item_id, read_at)
       VALUES (?, ?, ?, unixepoch())
       ON CONFLICT(member_id, corpus_id, item_id) DO UPDATE SET
         read_at = excluded.read_at
       RETURNING read_at`,
    )
    .bind(memberId, corpus.id, itemId)
    .first<{ read_at: number }>();
  if (!row) throw new Error("Reading progress was not saved");
  return { found: true, state: { readAt: Number(row.read_at) } };
}

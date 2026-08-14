import { type CorpusContext, corpusObjectKey } from "./corpus";

export type TranslationReviewAction = "approve" | "withdraw";

export interface TranslationReviewState {
  approvalCount: number;
  currentUserApproved: boolean;
  latestApprovalAt: number | null;
}

export interface TranslationReviewSummary {
  corpusId: string;
  reviewedItems: number;
  items: Record<string, TranslationReviewState>;
}

interface ReviewRow {
  item_id: string;
  approval_count: number;
  current_user_approved: number;
  latest_approval_at: number | null;
}

interface CorpusReviewItem {
  corpusId: string;
  id: string;
  segments: Array<{ english: string }>;
}

const reviewStateQuery = `
  WITH latest AS (
    SELECT event.*
    FROM translation_review_events AS event
    WHERE event.corpus_id = ?
      AND event.id = (
        SELECT MAX(candidate.id)
        FROM translation_review_events AS candidate
        WHERE candidate.corpus_id = event.corpus_id
          AND candidate.item_id = event.item_id
          AND candidate.reviewer_member_id = event.reviewer_member_id
      )
  )
  SELECT
    item_id,
    SUM(CASE WHEN action = 'approve' THEN 1 ELSE 0 END) AS approval_count,
    MAX(
      CASE
        WHEN reviewer_member_id = ? AND action = 'approve' THEN 1
        ELSE 0
      END
    ) AS current_user_approved,
    MAX(CASE WHEN action = 'approve' THEN recorded_at ELSE NULL END) AS latest_approval_at
  FROM latest
  GROUP BY item_id
  HAVING approval_count > 0 OR current_user_approved = 1`;

export function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  return origin !== null && origin === new URL(request.url).origin;
}

export function parseTranslationReviewAction(
  value: unknown,
): TranslationReviewAction | null {
  if (!value || typeof value !== "object") return null;
  const action = (value as { action?: unknown }).action;
  return action === "approve" || action === "withdraw" ? action : null;
}

export async function getTranslationReviewSummary(
  db: D1Database,
  reviewerMemberId: number | null,
  corpusId: string,
): Promise<TranslationReviewSummary> {
  const result = await db
    .prepare(reviewStateQuery)
    .bind(corpusId, reviewerMemberId ?? -1)
    .all<ReviewRow>();
  const items = Object.fromEntries(
    result.results.map((row) => [
      row.item_id,
      {
        approvalCount: Number(row.approval_count),
        currentUserApproved: Number(row.current_user_approved) === 1,
        latestApprovalAt:
          row.latest_approval_at === null
            ? null
            : Number(row.latest_approval_at),
      },
    ]),
  );
  return {
    corpusId,
    reviewedItems: Object.values(items).filter(
      (state) => state.approvalCount > 0,
    ).length,
    items,
  };
}

export async function recordTranslationReview(
  db: D1Database,
  bucket: R2Bucket,
  corpus: CorpusContext,
  reviewerMemberId: number,
  itemId: string,
  action: TranslationReviewAction,
): Promise<TranslationReviewState | null> {
  const object = await bucket.get(corpusObjectKey(corpus, "item", itemId));
  if (!object) return null;
  const serialized = await object.text();
  const item = JSON.parse(serialized) as Partial<CorpusReviewItem>;
  if (
    item.corpusId !== corpus.id ||
    item.id !== itemId ||
    !Array.isArray(item.segments) ||
    !item.segments.some(
      (segment) =>
        typeof segment?.english === "string" && segment.english.trim() !== "",
    )
  ) {
    throw new Error("Corpus review item is inconsistent");
  }

  const digest = await sha256Hex(serialized);
  await db
    .prepare(
      `INSERT INTO translation_review_events
        (reviewer_member_id, corpus_id, item_id, action, item_sha256)
       SELECT ?, ?, ?, ?, ?
       WHERE COALESCE(
         (
           SELECT action
           FROM translation_review_events
           WHERE corpus_id = ? AND item_id = ? AND reviewer_member_id = ?
           ORDER BY id DESC LIMIT 1
         ),
         ''
       ) <> ?`,
    )
    .bind(
      reviewerMemberId,
      corpus.id,
      itemId,
      action,
      digest,
      corpus.id,
      itemId,
      reviewerMemberId,
      action,
    )
    .run();

  const summary = await getTranslationReviewSummary(
    db,
    reviewerMemberId,
    corpus.id,
  );
  return (
    summary.items[itemId] ?? {
      approvalCount: 0,
      currentUserApproved: false,
      latestApprovalAt: null,
    }
  );
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

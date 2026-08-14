import { useState } from "react";

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

export interface TranslationReadState {
  readAt: number;
}

export interface TranslationReadSummary {
  corpusId: string;
  readItems: number;
  items: Record<string, TranslationReadState>;
}

export function TranslationApproval({
  itemId,
  state,
  onChange,
  ready = true,
  canApprove = true,
  readState,
  onReadChange,
  readStateReady = true,
}: {
  itemId: string;
  state?: TranslationReviewState;
  onChange: (state: TranslationReviewState) => void;
  ready?: boolean;
  canApprove?: boolean;
  readState?: TranslationReadState;
  onReadChange?: (state: TranslationReadState | null) => void;
  readStateReady?: boolean;
}) {
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [readBusy, setReadBusy] = useState(false);
  const [error, setError] = useState("");
  const approved = state?.currentUserApproved ?? false;
  const approvalCount = state?.approvalCount ?? 0;
  const hasRead = readState !== undefined;

  async function decide() {
    setApprovalBusy(true);
    setError("");
    try {
      const response = await fetch(
        `/api/corpus/al-isabah/reviews/${encodeURIComponent(itemId)}`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ action: approved ? "withdraw" : "approve" }),
        },
      );
      const body = (await response.json().catch(() => null)) as {
        state?: TranslationReviewState;
        error?: string;
      } | null;
      if (!response.ok || !body?.state) {
        throw new Error(
          body?.error ?? "The review decision could not be saved.",
        );
      }
      onChange(body.state);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The review decision could not be saved.",
      );
    } finally {
      setApprovalBusy(false);
    }
  }

  async function toggleRead() {
    setReadBusy(true);
    setError("");
    try {
      const response = await fetch(
        `/api/corpus/al-isabah/progress/${encodeURIComponent(itemId)}`,
        {
          method: hasRead ? "DELETE" : "PUT",
          credentials: "same-origin",
        },
      );
      const body = (await response.json().catch(() => null)) as {
        state?: TranslationReadState | null;
        error?: string;
      } | null;
      if (!response.ok || body?.state === undefined) {
        throw new Error(body?.error ?? "Reading progress could not be saved.");
      }
      onReadChange?.(body.state);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Reading progress could not be saved.",
      );
    } finally {
      setReadBusy(false);
    }
  }

  return (
    <section className="translation-approval" aria-label="Translation actions">
      <strong>
        {!ready
          ? "Loading human approval state…"
          : approvalCount > 0
            ? `Human reviewed · ${approvalCount} current ${approvalCount === 1 ? "approval" : "approvals"}`
            : "Awaiting human approval"}
      </strong>
      <div className="translation-action-buttons">
        {canApprove && (
          <button
            type="button"
            className={approved ? "button secondary" : "button"}
            disabled={approvalBusy || !ready}
            onClick={decide}
          >
            {!ready
              ? "Loading…"
              : approvalBusy
                ? "Saving…"
                : approved
                  ? "Withdraw my approval"
                  : "Approve this translation"}
          </button>
        )}
        {onReadChange && (
          <button
            type="button"
            className="button secondary"
            disabled={readBusy || !readStateReady}
            onClick={toggleRead}
          >
            {!readStateReady
              ? "Loading…"
              : readBusy
                ? "Saving…"
                : hasRead
                  ? "Mark unread"
                  : "Mark as read"}
          </button>
        )}
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

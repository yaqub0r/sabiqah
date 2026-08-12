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

export function TranslationApproval({
  itemId,
  state,
  onChange,
  ready = true,
}: {
  itemId: string;
  state?: TranslationReviewState;
  onChange: (state: TranslationReviewState) => void;
  ready?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const approved = state?.currentUserApproved ?? false;
  const approvalCount = state?.approvalCount ?? 0;

  async function decide() {
    setBusy(true);
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
      setBusy(false);
    }
  }

  return (
    <section className="translation-approval" aria-label="Translation approval">
      <div>
        <strong>
          {!ready
            ? "Loading human approval state…"
            : approvalCount > 0
              ? `Human reviewed · ${approvalCount} current ${approvalCount === 1 ? "approval" : "approvals"}`
              : "Awaiting human approval"}
        </strong>
        <p>
          Approval applies to this English translation in the pinned working
          corpus. It does not approve the Arabic source or publish the record.
        </p>
      </div>
      <button
        type="button"
        className={approved ? "button secondary" : "button"}
        disabled={busy || !ready}
        onClick={decide}
      >
        {!ready
          ? "Loading…"
          : busy
            ? "Saving…"
            : approved
              ? "Withdraw my approval"
              : "Approve this translation"}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

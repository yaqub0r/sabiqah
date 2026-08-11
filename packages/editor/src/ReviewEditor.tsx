import { useMemo, useState, type SyntheticEvent } from "react";

import {
  parseReviewProposal,
  type BookEntry,
  type ReviewProposal,
} from "@sabiqah/release-model";

export interface ReviewEditorProps {
  bookSlug: string;
  baseReleaseId: string;
  entry: BookEntry;
  onProposal?: (proposal: ReviewProposal) => void;
}

export function ReviewEditor({
  bookSlug,
  baseReleaseId,
  entry,
  onProposal,
}: ReviewEditorProps) {
  const [segmentId, setSegmentId] = useState(entry.segments[0]?.id ?? "");
  const segment = useMemo(
    () => entry.segments.find((candidate) => candidate.id === segmentId),
    [entry.segments, segmentId],
  );
  const [target, setTarget] = useState<"translation" | "canonical_arabic">(
    "translation",
  );
  const [proposedText, setProposedText] = useState(segment?.english.text ?? "");
  const [rationale, setRationale] = useState("");
  const [evidence, setEvidence] = useState("");
  const [error, setError] = useState("");
  const [proposal, setProposal] = useState<ReviewProposal>();

  function selectSegment(nextSegmentId: string) {
    const nextSegment = entry.segments.find(
      (candidate) => candidate.id === nextSegmentId,
    );
    setSegmentId(nextSegmentId);
    setProposedText(
      target === "translation"
        ? (nextSegment?.english.text ?? "")
        : (nextSegment?.arabic.text ?? ""),
    );
  }

  function selectTarget(nextTarget: "translation" | "canonical_arabic") {
    setTarget(nextTarget);
    setProposedText(
      nextTarget === "translation"
        ? (segment?.english.text ?? "")
        : (segment?.arabic.text ?? ""),
    );
  }

  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const result = parseReviewProposal({
      proposalVersion: "1.0.0",
      bookSlug,
      baseReleaseId,
      entryId: entry.id,
      createdAt: new Date().toISOString(),
      operations: [
        {
          segmentId,
          target,
          proposedText,
          rationale,
          evidenceRefs: evidence
            .split("\n")
            .map((value) => value.trim())
            .filter(Boolean),
        },
      ],
    });

    setProposal(result);
    setError("");
    onProposal?.(result);
  }

  function safelySubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    try {
      submit(event);
    } catch (caught) {
      setProposal(undefined);
      setError(
        caught instanceof Error ? caught.message : "The proposal is not valid.",
      );
    }
  }

  return (
    <section className="review-editor" aria-labelledby="review-editor-title">
      <div className="editor-heading">
        <p className="eyebrow">Review proposal</p>
        <h2 id="review-editor-title">{entry.title.en}</h2>
        <p>
          The source remains unchanged until a book maintainer reviews and
          merges a pull request.
        </p>
      </div>

      <form onSubmit={safelySubmit}>
        <label>
          Segment
          <select
            value={segmentId}
            onChange={(event) => selectSegment(event.target.value)}
          >
            {entry.segments.map((candidate, index) => (
              <option value={candidate.id} key={candidate.id}>
                Segment {index + 1}
              </option>
            ))}
          </select>
        </label>

        <fieldset>
          <legend>What are you proposing?</legend>
          <label className="choice">
            <input
              type="radio"
              checked={target === "translation"}
              onChange={() => selectTarget("translation")}
            />
            English translation
          </label>
          <label className="choice protected-choice">
            <input
              type="radio"
              checked={target === "canonical_arabic"}
              onChange={() => selectTarget("canonical_arabic")}
            />
            Protected Arabic correction
          </label>
        </fieldset>

        <div className="source-preview">
          <span>Canonical Arabic</span>
          <p dir="rtl" lang="ar">
            {segment?.arabic.text}
          </p>
          <small>Review state: {segment?.arabic.reviewState}</small>
        </div>

        <label>
          Proposed text
          <textarea
            dir={target === "canonical_arabic" ? "rtl" : "ltr"}
            value={proposedText}
            onChange={(event) => setProposedText(event.target.value)}
            rows={6}
            required
          />
        </label>

        <label>
          Rationale{" "}
          {target === "canonical_arabic" ? "(required)" : "(recommended)"}
          <textarea
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
            rows={3}
          />
        </label>

        <label>
          Evidence references, one per line{" "}
          {target === "canonical_arabic" ? "(required)" : ""}
          <textarea
            value={evidence}
            onChange={(event) => setEvidence(event.target.value)}
            rows={3}
          />
        </label>

        {target === "canonical_arabic" && (
          <p className="protected-note" role="note">
            Arabic corrections use a protected review path and must cite source
            evidence.
          </p>
        )}
        {error && <p className="form-error">{error}</p>}
        <button type="submit">Prepare proposal</button>
      </form>

      {proposal && (
        <div className="proposal-ready" role="status">
          <strong>Proposal prepared.</strong>
          <p>
            The Decap adapter can now submit this object through a fork-based
            pull request.
          </p>
          <pre>{JSON.stringify(proposal, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}

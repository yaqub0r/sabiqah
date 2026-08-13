import {
  parseReviewCorpusItem,
  type ReviewCorpusItem,
} from "@sabiqah/release-model";
import { useEffect, useState } from "react";

import { CorpusAccess } from "./CorpusAccess";
import { HonorificText } from "./HonorificText";
import {
  TranslationApproval,
  type TranslationReviewState,
  type TranslationReviewSummary,
} from "./TranslationApproval";

interface SessionIdentity {
  login: string;
  membershipStatus: "active" | "limited" | "suspended";
}

export function CorpusItemReview({ siteKey }: { siteKey?: string }) {
  const [session, setSession] = useState<
    "loading" | "anonymous" | "active" | "limited"
  >("loading");
  const [identity, setIdentity] = useState<SessionIdentity>();
  const [item, setItem] = useState<ReviewCorpusItem>();
  const [reviewState, setReviewState] = useState<TranslationReviewState>();
  const [error, setError] = useState("");
  const [itemId, setItemId] = useState("");

  useEffect(() => {
    setItemId(new URLSearchParams(window.location.search).get("id") ?? "");
  }, []);

  useEffect(() => {
    fetch("/api/session", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error("anonymous");
        return (await response.json()) as { identity: SessionIdentity };
      })
      .then(({ identity: nextIdentity }) => {
        setIdentity(nextIdentity);
        setSession(
          nextIdentity.membershipStatus === "active" ? "active" : "limited",
        );
      })
      .catch(() => setSession("anonymous"));
  }, []);

  useEffect(() => {
    if (session !== "active" || !itemId) return;
    if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$/.test(itemId)) {
      setError("Choose an item from the working corpus.");
      return;
    }
    Promise.all([
      fetch(`/api/corpus/al-isabah/items/${encodeURIComponent(itemId)}`, {
        credentials: "same-origin",
      }).then(async (response) => {
        if (!response.ok) throw new Error("This review item is not available.");
        return parseReviewCorpusItem(await response.json());
      }),
      fetch("/api/corpus/al-isabah/reviews", {
        credentials: "same-origin",
      }).then(async (response) => {
        if (!response.ok)
          throw new Error("Human review state could not be loaded.");
        return (await response.json()) as TranslationReviewSummary;
      }),
    ])
      .then(([nextItem, reviews]) => {
        setItem(nextItem);
        setReviewState(reviews.items[nextItem.id]);
      })
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "The item could not be loaded.",
        ),
      );
  }, [itemId, session]);

  if (session === "loading") return <p>Checking reviewer access…</p>;
  if (session === "anonymous")
    return (
      <CorpusAccess
        siteKey={siteKey}
        returnTo={`/works/al-isabah/review/?id=${encodeURIComponent(itemId)}`}
      />
    );
  if (session === "limited")
    return (
      <p className="issue-banner">
        @{identity?.login} can read this record in the public edition, but does
        not currently have access to submit a review.
      </p>
    );
  if (error) return <p className="issue-banner">{error}</p>;
  if (!item) return <p>Loading review item…</p>;

  return (
    <article className="corpus-review-item">
      <header className="entry-title">
        <div>
          <p className="eyebrow">
            {item.kind} · Volume {item.volume} · @{identity?.login}
          </p>
          <h1>
            <HonorificText text={item.title.en} language="en" />
          </h1>
        </div>
        <p className="arabic-title" lang="ar" dir="rtl">
          <HonorificText text={item.title.ar} language="ar" />
        </p>
      </header>
      <aside className="issue-banner">
        <strong>Canonical promotion blocked.</strong> This is a publicly
        consumable working record, not a human-approved scholarly release.
      </aside>
      <div className="review-state-bar">
        <span className="badge">
          Translation: {item.translationState.replaceAll("_", " ")}
        </span>
        <span
          className={`badge ${item.machineAssessment === "needs_attention" ? "warning" : ""}`}
        >
          Machine: {item.machineAssessment.replaceAll("_", " ")}
        </span>
        <span className="badge warning">
          Human: {item.humanReview.replaceAll("_", " ")}
        </span>
      </div>
      {item.relationship && (
        <p>
          <strong>Relationship:</strong> {item.relationship}
        </p>
      )}
      {item.rationale && (
        <p>
          <strong>Why included:</strong> {item.rationale}
        </p>
      )}
      {item.segments.map((segment) => (
        <section className="bilingual-segment" id={segment.id} key={segment.id}>
          <div className="english-column" lang="en" dir="ltr">
            <p className="corpus-text">
              {segment.english ? (
                <HonorificText text={segment.english} language="en" />
              ) : (
                "English text is contained in the entry heading."
              )}
            </p>
            <p className="segment-meta">
              {segment.machineState.replaceAll("_", " ")}
            </p>
          </div>
          <div className="arabic-column" lang="ar" dir="rtl">
            <p className="arabic corpus-text">
              {segment.arabic ? (
                <HonorificText text={segment.arabic} language="ar" />
              ) : (
                "Arabic source text is not included in this review record."
              )}
            </p>
            <p className="segment-meta">
              {segment.pages
                .map(
                  (page) =>
                    `vol. ${page.volume}, p. ${page.printedPage ?? "?"}`,
                )
                .join(" · ")}
            </p>
          </div>
        </section>
      ))}
      {item.translationState === "translated" ? (
        <TranslationApproval
          itemId={item.id}
          state={reviewState}
          onChange={setReviewState}
        />
      ) : (
        <p className="issue-banner">
          This Arabic-only record has no translation to approve. Add or correct
          the translation before submitting an approval.
        </p>
      )}
      {item.unresolved.length > 0 && (
        <section className="review-notes">
          <h2>Unresolved work</h2>
          {item.unresolved.map((note, index) => (
            <article key={`${note.category}-${index}`}>
              <h3>{note.category.replaceAll("_", " ")}</h3>
              {note.arabicSpan && (
                <p lang="ar" dir="rtl">
                  <HonorificText text={note.arabicSpan} language="ar" />
                </p>
              )}
              <p>{note.explanation}</p>
            </article>
          ))}
        </section>
      )}
      {item.decisions && item.decisions.length > 0 && (
        <section className="review-notes">
          <h2>Editorial decisions</h2>
          {item.decisions.map((decision) => (
            <article key={decision.issue}>
              <h3>{decision.issue}</h3>
              <p>
                <strong>Resolution:</strong> {decision.resolution}
              </p>
              <p>
                <strong>Basis:</strong> {decision.basis}
              </p>
            </article>
          ))}
        </section>
      )}
      <section className="workflow-timeline">
        <h2>Workflow history</h2>
        <ol>
          {item.workflowStages.map((stage, index) => (
            <li key={`${stage.stage}-${index}`}>
              <div>
                <h3>{stage.stage.replaceAll("_", " ")}</h3>
                <span
                  className={`badge ${stage.state === "complete" ? "" : "warning"}`}
                >
                  {stage.state.replaceAll("_", " ")}
                </span>
              </div>
              <p>{stage.summary}</p>
              {stage.englishText && (
                <details>
                  <summary>View this stage's English text</summary>
                  <p className="corpus-text">{stage.englishText}</p>
                </details>
              )}
              {stage.issues && stage.issues.length > 0 && (
                <div className="stage-issues">
                  {stage.issues.map((issue, issueIndex) => (
                    <article key={`${issue.category}-${issueIndex}`}>
                      <strong>
                        {issue.severity}: {issue.category}
                      </strong>
                      <p>{issue.explanation}</p>
                      {issue.suggestedFix && (
                        <p>
                          <strong>Suggested fix:</strong> {issue.suggestedFix}
                        </p>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      </section>
      <section className="source-list">
        <h2>Provenance</h2>
        <p>
          Source authority:{" "}
          {"sourceArtifactId" in item.provenance ? (
            <code>{item.provenance.sourceArtifactId}</code>
          ) : (
            <code>{item.provenance.sourceAuthorityId}</code>
          )}
        </p>
        <p>
          Integrity: <code>{item.provenance.sourceArtifactSha256}</code>
        </p>
      </section>
      <div className="actions">
        <a className="button secondary" href="/works/al-isabah/">
          Back to corpus
        </a>
      </div>
    </article>
  );
}

import {
  parseReviewCorpusIndex,
  parseReviewCorpusSummary,
  type ReviewCorpusIndex,
  type ReviewCorpusSummary,
} from "@sabiqah/release-model";
import { useEffect, useMemo, useState } from "react";

import type { TranslationReviewSummary } from "./TranslationApproval";

function coveragePercent(completed: number, total: number) {
  return total === 0 ? 0 : Math.round((completed / total) * 100);
}

function coverageStateLabel(
  availability: ReviewCorpusSummary["volumes"][number]["availability"],
) {
  if (availability === "complete_translation")
    return "Complete working translation";
  if (availability === "selected_passages")
    return "Partial working translation";
  return "Not yet translated";
}

export function CorpusCoverage() {
  const [summary, setSummary] = useState<ReviewCorpusSummary>();
  const [index, setIndex] = useState<ReviewCorpusIndex>();
  const [reviews, setReviews] = useState<TranslationReviewSummary>();
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("/api/corpus/al-isabah/summary", {
        credentials: "same-origin",
      }).then(async (response) => {
        if (!response.ok) throw new Error("Coverage is not available.");
        return parseReviewCorpusSummary(await response.json());
      }),
      fetch("/api/corpus/al-isabah/index", { credentials: "same-origin" }).then(
        async (response) => {
          if (!response.ok) throw new Error("Coverage is not available.");
          return parseReviewCorpusIndex(await response.json());
        },
      ),
      fetch("/api/corpus/al-isabah/reviews", {
        credentials: "same-origin",
      }).then(async (response) => {
        if (!response.ok)
          throw new Error("Human-review coverage is not available.");
        return (await response.json()) as TranslationReviewSummary;
      }),
    ])
      .then(([nextSummary, nextIndex, nextReviews]) => {
        setSummary(nextSummary);
        setIndex(nextIndex);
        setReviews(nextReviews);
      })
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Coverage could not be loaded.",
        ),
      );
  }, []);

  const volumes = useMemo(
    () =>
      summary?.volumes.map((volume) => {
        const sourceCount = volume.sourceItemCount ?? volume.itemCount;
        const volumeItems =
          index?.items.filter((item) => item.volume === volume.number) ?? [];
        const reviewedCount = volumeItems.filter(
          (item) => (reviews?.items[item.id]?.approvalCount ?? 0) > 0,
        ).length;
        return {
          ...volume,
          sourceCount,
          reviewedCount,
          translationPercent: coveragePercent(volume.itemCount, sourceCount),
          reviewPercent: coveragePercent(reviewedCount, volume.itemCount),
        };
      }) ?? [],
    [index, reviews, summary],
  );

  if (error) return <p className="issue-banner">{error}</p>;
  if (!summary || !index || !reviews)
    return <p className="loading-state">Loading live coverage…</p>;

  return (
    <section className="edition-overview" aria-labelledby="coverage-title">
      <div>
        <p className="eyebrow">Live edition coverage</p>
        <h1 id="coverage-title">Coverage by source volume</h1>
        <p className="lede">
          Translation coverage follows the deployed, source-locked corpus.
          Human-review progress reflects current approvals.
        </p>
      </div>
      <div className="volume-shelf" aria-label="Live coverage by volume">
        {volumes.map((volume) => (
          <article
            className={`coverage-card${volume.itemCount === 0 ? " unavailable" : ""}`}
            aria-label={`Volume ${volume.number}: ${volume.itemCount.toLocaleString()} of ${volume.sourceCount.toLocaleString()} source entries translated; ${volume.reviewedCount.toLocaleString()} of ${volume.itemCount.toLocaleString()} translations human reviewed; ${coverageStateLabel(volume.availability)}`}
            key={volume.id}
          >
            <span className="volume-label">Volume</span>
            <strong>{volume.number}</strong>
            <span className="coverage-state">
              {coverageStateLabel(volume.availability)}
            </span>
            <span className="coverage-stat">
              <span>
                <b>{volume.translationPercent}%</b> translated
              </span>
              <small>
                {volume.itemCount.toLocaleString()} of{" "}
                {volume.sourceCount.toLocaleString()} source entries
              </small>
              <span className="coverage-meter" aria-hidden="true">
                <span style={{ width: `${volume.translationPercent}%` }} />
              </span>
            </span>
            <span className="coverage-stat">
              <span>
                <b>{volume.reviewPercent}%</b> human reviewed
              </span>
              <small>
                {volume.reviewedCount.toLocaleString()} of{" "}
                {volume.itemCount.toLocaleString()} translations
              </small>
              <span className="coverage-meter review" aria-hidden="true">
                <span style={{ width: `${volume.reviewPercent}%` }} />
              </span>
            </span>
            {volume.itemCount > 0 ? (
              <span className="coverage-actions">
                <a href={`/works/al-isabah/?volume=${volume.number}`}>
                  Read volume
                </a>
                <a
                  href={`/works/al-isabah/?volume=${volume.number}&review=unreviewed`}
                >
                  Review remaining translations
                </a>
              </span>
            ) : (
              <span className="coverage-unavailable">
                Reading not available
              </span>
            )}
          </article>
        ))}
      </div>
      <p className="edition-status">
        {summary.counts.translated.toLocaleString()} translated records ·{" "}
        {summary.counts.unresolvedItems.toLocaleString()} unresolved items ·{" "}
        {reviews.reviewedItems.toLocaleString()} human reviewed
        {summary.exclusions &&
          summary.exclusions.contextualPassagesPendingPublicSourceAlignment >
            0 &&
          ` · ${summary.exclusions.contextualPassagesPendingPublicSourceAlignment.toLocaleString()} contextual passages excluded pending public-source alignment`}
      </p>
    </section>
  );
}

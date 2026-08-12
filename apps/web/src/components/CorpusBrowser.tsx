import {
  parseReviewCorpusIndex,
  parseReviewCorpusSummary,
  type ReviewCorpusIndex,
  type ReviewCorpusSummary,
} from "@sabiqah/release-model";
import { useEffect, useMemo, useState } from "react";

import { CorpusAccess } from "./CorpusAccess";

interface SessionIdentity {
  login: string;
  membershipStatus: "active" | "limited" | "suspended";
}

const PAGE_SIZE = 50;

export function CorpusBrowser({ siteKey }: { siteKey?: string }) {
  const [summary, setSummary] = useState<ReviewCorpusSummary>();
  const [index, setIndex] = useState<ReviewCorpusIndex>();
  const [identity, setIdentity] = useState<SessionIdentity>();
  const [session, setSession] = useState<
    "loading" | "anonymous" | "active" | "limited"
  >("loading");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState("all");
  const [state, setState] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetch("/api/corpus/al-isabah/summary", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("The corpus inventory is not available.");
        return parseReviewCorpusSummary(await response.json());
      })
      .then(setSummary)
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "The corpus inventory could not be loaded.",
        ),
      );

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
    if (session !== "active") return;
    fetch("/api/corpus/al-isabah/index", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("The protected corpus index could not be loaded.");
        return parseReviewCorpusIndex(await response.json());
      })
      .then(setIndex)
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "The corpus index could not be loaded.",
        ),
      );
  }, [session]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return (index?.items ?? []).filter((item) => {
      const matchesQuery =
        !normalized ||
        item.titleEn.toLocaleLowerCase().includes(normalized) ||
        item.titleAr.includes(query.trim()) ||
        String(item.printedEntryNumber ?? "").includes(normalized);
      const matchesCollection =
        collection === "all" || item.collectionIds.includes(collection);
      const matchesState =
        state === "all" ||
        (state === "needs_attention" &&
          item.machineAssessment === "needs_attention") ||
        (state === "unresolved" && item.unresolvedCount > 0) ||
        item.humanReview === state;
      return matchesQuery && matchesCollection && matchesState;
    });
  }, [collection, index, query, state]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function resetPage() {
    setPage(1);
  }

  return (
    <>
      {error && <p className="issue-banner">{error}</p>}
      {summary && (
        <>
          <div className="corpus-stats" aria-label="Corpus progress">
            <article>
              <strong>{summary.counts.entries.toLocaleString()}</strong>
              <span>translated biographies</span>
            </article>
            <article>
              <strong>{summary.counts.contextualPassages}</strong>
              <span>contextual passages</span>
            </article>
            <article>
              <strong>{summary.counts.needsAttention}</strong>
              <span>need attention</span>
            </article>
            <article>
              <strong>{summary.counts.unresolvedItems}</strong>
              <span>unresolved items</span>
            </article>
            <article>
              <strong>{summary.counts.humanReviewed}</strong>
              <span>human reviewed</span>
            </article>
          </div>
          <div className="collection-grid">
            {summary.collections.map((candidate) => (
              <article key={candidate.id}>
                <p className="eyebrow">
                  {candidate.kind} · {candidate.itemCount.toLocaleString()}{" "}
                  items
                </p>
                <h2>{candidate.title}</h2>
                <p>{candidate.description}</p>
                <span className="badge warning">
                  {candidate.reviewState.replaceAll("_", " ")}
                </span>
              </article>
            ))}
          </div>
          {summary.coverage && (
            <details className="coverage-accounting">
              <summary>View Khadijah coverage accounting</summary>
              <p>
                {summary.coverage.sourceResults} unique source-result blocks
                received an explicit inclusion or exclusion decision.
              </p>
              <dl>
                {Object.entries(summary.coverage.decisions).map(
                  ([decision, count]) => (
                    <div key={decision}>
                      <dt>{decision.replaceAll("_", " ")}</dt>
                      <dd>{count}</dd>
                    </div>
                  ),
                )}
              </dl>
            </details>
          )}
        </>
      )}

      {session === "loading" && <p>Checking reviewer access…</p>}
      {session === "anonymous" && (
        <CorpusAccess siteKey={siteKey} returnTo="/works/al-isabah/" />
      )}
      {session === "limited" && (
        <p className="issue-banner">
          @{identity?.login} does not currently have access to restricted review
          text.
        </p>
      )}
      {session === "active" && (
        <section
          className="corpus-browser"
          aria-labelledby="working-corpus-title"
        >
          <div className="section-heading">
            <div>
              <p className="eyebrow">Authenticated review corpus</p>
              <h2 id="working-corpus-title">Browse every available item</h2>
            </div>
            <span className="badge">@{identity?.login}</span>
          </div>
          <div className="corpus-filters">
            <label>
              Search
              <input
                type="search"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  resetPage();
                }}
                placeholder="Name, Arabic title, or entry number"
              />
            </label>
            <label>
              Collection
              <select
                value={collection}
                onChange={(event) => {
                  setCollection(event.target.value);
                  resetPage();
                }}
              >
                <option value="all">All work</option>
                <option value="volume-08">Volume 8</option>
                <option value="khadijah-immediate">Khadijah cohort</option>
                <option value="khadijah-context">Khadijah contexts</option>
              </select>
            </label>
            <label>
              Review state
              <select
                value={state}
                onChange={(event) => {
                  setState(event.target.value);
                  resetPage();
                }}
              >
                <option value="all">All states</option>
                <option value="needs_attention">Needs attention</option>
                <option value="unresolved">Has unresolved items</option>
                <option value="unreviewed">Human review pending</option>
                <option value="reviewed">Reviewed</option>
                <option value="verified">Verified</option>
              </select>
            </label>
          </div>
          <p className="result-count">
            Showing {visible.length.toLocaleString()} of{" "}
            {filtered.length.toLocaleString()} matching items.
          </p>
          <ol
            className="entry-list corpus-list"
            start={(page - 1) * PAGE_SIZE + 1}
          >
            {visible.map((item) => (
              <li key={item.id}>
                <a
                  className="entry-card"
                  href={`/works/al-isabah/review/?id=${encodeURIComponent(item.id)}`}
                >
                  <span className="entry-number">
                    {item.printedEntryNumber ?? `C${item.sequence}`}
                  </span>
                  <span>
                    <h3>{item.titleEn}</h3>
                    <p lang="ar" dir="rtl">
                      {item.titleAr || item.relationship}
                    </p>
                    <small>
                      Volume {item.volume} · {item.kind}
                    </small>
                  </span>
                  <span
                    className={`badge ${item.machineAssessment === "needs_attention" || item.unresolvedCount ? "warning" : ""}`}
                  >
                    {item.unresolvedCount
                      ? `${item.unresolvedCount} unresolved`
                      : item.machineAssessment.replaceAll("_", " ")}
                  </span>
                </a>
              </li>
            ))}
          </ol>
          <nav className="pagination" aria-label="Corpus pages">
            <button
              className="button secondary"
              disabled={page <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              Previous
            </button>
            <span>
              Page {page} of {pageCount}
            </span>
            <button
              className="button secondary"
              disabled={page >= pageCount}
              onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
            >
              Next
            </button>
          </nav>
        </section>
      )}
    </>
  );
}

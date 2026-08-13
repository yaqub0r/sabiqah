import {
  parseReviewCorpusIndex,
  parseReviewCorpusSection,
  parseReviewCorpusSummary,
  normalizeHonorificSearch,
  type ReviewCorpusIndex,
  type ReviewCorpusItem,
  type ReviewCorpusSection,
  type ReviewCorpusSummary,
} from "@sabiqah/release-model";
import { Fragment, useEffect, useMemo, useState } from "react";

import { CorpusAccess } from "./CorpusAccess";
import { HonorificText } from "./HonorificText";
import { SelectionReporter } from "./SelectionReporter";
import {
  TranslationApproval,
  type TranslationReviewState,
  type TranslationReviewSummary,
} from "./TranslationApproval";

interface SessionIdentity {
  login: string;
  membershipStatus: "active" | "limited" | "suspended";
}

interface SectionLink {
  id: string;
  volume: number;
  label: string;
  itemCount: number;
}

interface EnglishReadingBlock {
  kind: "prose" | "poetry";
  paragraphs: string[];
  meter?: string;
  continuation?: string;
}

const METER_LABEL =
  /^Meter:\s*(al-[\p{L}\p{M}-]+)(?:\s+(And the remaining verses\.))?$/iu;

export function englishReadingBlocks(text: string): EnglishReadingBlock[] {
  const paragraphs = text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
  const poetryByStart = new Map<
    number,
    { end: number; meter: string; continuation?: string }
  >();

  for (let meterIndex = 0; meterIndex < paragraphs.length; meterIndex += 1) {
    const meter = paragraphs[meterIndex]?.match(METER_LABEL);
    if (!meter || meterIndex === 0) continue;
    let start = meterIndex - 1;
    while (
      start > 0 &&
      meterIndex - start < 12 &&
      !paragraphs[start - 1]?.endsWith(":") &&
      !paragraphs[start - 1]?.match(METER_LABEL)
    ) {
      start -= 1;
    }
    poetryByStart.set(start, {
      end: meterIndex,
      meter: meter[1]!,
      continuation: meter[2],
    });
  }

  const blocks: EnglishReadingBlock[] = [];
  for (let index = 0; index < paragraphs.length; index += 1) {
    const poetry = poetryByStart.get(index);
    if (poetry) {
      blocks.push({
        kind: "poetry",
        paragraphs: paragraphs.slice(index, poetry.end),
        meter: poetry.meter,
        continuation: poetry.continuation,
      });
      index = poetry.end;
      continue;
    }
    blocks.push({ kind: "prose", paragraphs: [paragraphs[index]!] });
  }
  return blocks;
}

function EnglishReadingText({ text }: { text: string }) {
  return englishReadingBlocks(text).map((block, index) =>
    block.kind === "poetry" ? (
      <figure className="poetry-block" key={`poetry-${index}`}>
        <blockquote aria-label="Poetry">
          {block.paragraphs.map((paragraph, paragraphIndex) => (
            <p key={paragraphIndex}>
              <HonorificText text={paragraph} language="en" />
            </p>
          ))}
        </blockquote>
        <figcaption>Meter: {block.meter}</figcaption>
        {block.continuation && <p>{block.continuation}</p>}
      </figure>
    ) : (
      <p className="corpus-text" key={`prose-${index}`}>
        <HonorificText text={block.paragraphs[0]!} language="en" />
      </p>
    ),
  );
}

function ArabicReadingText({ text }: { text: string }) {
  return text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph, index) => {
      const lines = paragraph.split("\n").map((line) => line.trim());
      if (lines.length === 1) {
        return (
          <p className="arabic corpus-text" key={index}>
            <HonorificText text={paragraph} language="ar" />
          </p>
        );
      }
      return (
        <Fragment key={index}>
          <p className="arabic corpus-text">
            <HonorificText text={lines[0]!} language="ar" />
          </p>
          <div className="arabic arabic-poetry" aria-label="Poetry">
            {lines.slice(1).map((line, lineIndex) => (
              <p key={lineIndex}>
                <HonorificText text={line} language="ar" />
              </p>
            ))}
          </div>
        </Fragment>
      );
    });
}

function sectionLinks(index: ReviewCorpusIndex, volume: number): SectionLink[] {
  const grouped = new Map<string, ReviewCorpusIndex["items"]>();
  for (const item of index.items.filter(
    (candidate) => candidate.volume === volume,
  )) {
    grouped.set(item.sectionId, [...(grouped.get(item.sectionId) ?? []), item]);
  }
  return [...grouped.entries()].map(([id, items]) => {
    const pageRange = id.match(/pages-(\d{4})-(\d{4})$/);
    return {
      id,
      volume,
      label:
        volume === 8 && pageRange
          ? `Pages ${Number(pageRange[1])}–${Number(pageRange[2])}`
          : "Selected translated passages",
      itemCount: items.length,
    };
  });
}

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

function ReviewEvidence({ item }: { item: ReviewCorpusItem }) {
  return (
    <details className="record-evidence">
      <summary>
        Review record
        {item.unresolved.length > 0 &&
          ` · ${item.unresolved.length} unresolved`}
      </summary>
      {item.unresolved.length > 0 && (
        <section>
          <h4>Unresolved work</h4>
          {item.unresolved.map((note, index) => (
            <article key={`${note.category}-${index}`}>
              <strong>{note.category.replaceAll("_", " ")}</strong>
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
        <section>
          <h4>Editorial decisions</h4>
          {item.decisions.map((decision) => (
            <article key={decision.issue}>
              <strong>{decision.issue}</strong>
              <p>{decision.resolution}</p>
              <small>{decision.basis}</small>
            </article>
          ))}
        </section>
      )}
      <section>
        <h4>Translation workflow</h4>
        <ol className="compact-workflow">
          {item.workflowStages.map((stage, index) => (
            <li key={`${stage.stage}-${index}`}>
              <strong>{stage.stage.replaceAll("_", " ")}</strong>
              <span
                className={`badge ${stage.state === "complete" ? "" : "warning"}`}
              >
                {stage.state.replaceAll("_", " ")}
              </span>
              <p>{stage.summary}</p>
              {stage.englishText && (
                <details>
                  <summary>View this stage’s English text</summary>
                  <p className="corpus-text">{stage.englishText}</p>
                </details>
              )}
              {stage.issues?.map((issue, issueIndex) => (
                <article key={`${issue.category}-${issueIndex}`}>
                  <strong>
                    {issue.severity}: {issue.category}
                  </strong>
                  <p>{issue.explanation}</p>
                  {issue.suggestedFix && (
                    <p>Suggested fix: {issue.suggestedFix}</p>
                  )}
                </article>
              ))}
            </li>
          ))}
        </ol>
      </section>
      <p className="provenance-line">
        {item.source ? (
          <>
            Public source{" "}
            <a href={item.source.sourceUrl}>
              OpenITI entry {item.source.entryNumber}
            </a>{" "}
            · {item.source.license.spdx} · integrity{" "}
            <code>{item.source.sourceTextSha256}</code>
          </>
        ) : (
          <>
            Provenance{" "}
            <code>
              {"sourceArtifactId" in item.provenance
                ? item.provenance.sourceArtifactId
                : item.provenance.sourceAuthorityId}
            </code>{" "}
            · integrity <code>{item.provenance.sourceArtifactSha256}</code>
          </>
        )}
      </p>
    </details>
  );
}

function ReadingRecord({
  item,
  reviewState,
  onReviewStateChange,
  reviewStateLoaded,
  canReview,
}: {
  item: ReviewCorpusItem;
  reviewState?: TranslationReviewState;
  onReviewStateChange: (state: TranslationReviewState) => void;
  reviewStateLoaded: boolean;
  canReview: boolean;
}) {
  const pages = [
    ...new Set(
      item.segments.flatMap((segment) =>
        segment.pages
          .map((page) => page.printedPage)
          .filter((page): page is number => page !== null),
      ),
    ),
  ];
  const englishLength = item.segments.reduce(
    (total, segment) => total + segment.english.trim().length,
    0,
  );
  const isShort = item.segments.length === 1 && englishLength < 280;
  return (
    <Fragment>
      {item.headingsBefore && item.headingsBefore.length > 0 && (
        <header className="source-structure-heading">
          {item.headingsBefore.map((heading) => (
            <div key={`${heading.level}-${heading.ar}`}>
              <p className="eyebrow">{heading.level}</p>
              <h2>{heading.en}</h2>
              <p lang="ar" dir="rtl">
                {heading.ar}
              </p>
              {heading.noteEn && (
                <p className="source-structure-note">{heading.noteEn}</p>
              )}
              {heading.noteAr && (
                <p className="source-structure-note" lang="ar" dir="rtl">
                  {heading.noteAr}
                </p>
              )}
            </div>
          ))}
        </header>
      )}
      <article
        className={`reading-record${isShort ? " short-record" : ""}`}
        id={item.id}
      >
        <header>
          <p className="record-number">
            {item.printedEntryNumber
              ? `Entry ${item.printedEntryNumber}`
              : "Translated passage"}
            {pages.length > 0 && ` · p. ${pages.join("–")}`}
          </p>
          <div>
            <h3
              data-report-item-id={item.id}
              data-report-segment-id="title"
              data-report-field="title"
              data-report-language="English"
            >
              <HonorificText text={item.title.en} language="en" />
            </h3>
            <p
              lang="ar"
              dir="rtl"
              data-report-item-id={item.id}
              data-report-segment-id="title"
              data-report-field="title"
              data-report-language="Arabic"
            >
              <HonorificText text={item.title.ar} language="ar" />
            </p>
          </div>
        </header>
        {item.relationship && (
          <p className="passage-context">{item.relationship}</p>
        )}
        {item.segments.map((segment) => (
          <section className="reading-bilingual" key={segment.id}>
            <div
              lang="en"
              dir="ltr"
              data-report-item-id={item.id}
              data-report-segment-id={segment.id}
              data-report-field="segment"
              data-report-language="English"
            >
              {segment.english ? (
                <EnglishReadingText text={segment.english} />
              ) : (
                <p className="corpus-text continuation-note">
                  English text is contained in the entry heading.
                </p>
              )}
            </div>
            <div
              lang="ar"
              dir="rtl"
              data-report-item-id={item.id}
              data-report-segment-id={segment.id}
              data-report-field="segment"
              data-report-language="Arabic"
            >
              <ArabicReadingText text={segment.arabic} />
            </div>
          </section>
        ))}
        {canReview && item.translationState === "translated" && (
          <TranslationApproval
            itemId={item.id}
            state={reviewState}
            onChange={onReviewStateChange}
            ready={reviewStateLoaded}
          />
        )}
        {canReview && item.translationState === "untranslated" && (
          <p className="issue-banner">
            This Arabic-only record has no translation to approve. Add or
            correct the translation through the review workspace first.
          </p>
        )}
        <ReviewEvidence item={item} />
      </article>
    </Fragment>
  );
}

export function CorpusReader({ siteKey }: { siteKey?: string }) {
  const [summary, setSummary] = useState<ReviewCorpusSummary>();
  const [index, setIndex] = useState<ReviewCorpusIndex>();
  const [section, setSection] = useState<ReviewCorpusSection>();
  const [reviewSummary, setReviewSummary] =
    useState<TranslationReviewSummary>();
  const [identity, setIdentity] = useState<SessionIdentity>();
  const [session, setSession] = useState<
    "loading" | "anonymous" | "active" | "limited"
  >("loading");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedVolume, setSelectedVolume] = useState(8);
  const [selectedSectionId, setSelectedSectionId] = useState("");
  const [pendingAnchor, setPendingAnchor] = useState("");
  const [hideReviewed, setHideReviewed] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const volume = Number(params.get("volume"));
    if (Number.isInteger(volume) && volume > 0) setSelectedVolume(volume);
    setSelectedSectionId(params.get("section") ?? "");
    setPendingAnchor(window.location.hash.slice(1));

    fetch("/api/corpus/al-isabah/summary", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("The edition overview is not available.");
        return parseReviewCorpusSummary(await response.json());
      })
      .then(setSummary)
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "The edition could not be loaded.",
        ),
      );

    fetch("/api/corpus/al-isabah/index", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("The public table of contents could not be loaded.");
        return parseReviewCorpusIndex(await response.json());
      })
      .then(setIndex)
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "The table of contents could not be loaded.",
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
    fetch("/api/corpus/al-isabah/reviews", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("Human review state could not be loaded.");
        return (await response.json()) as TranslationReviewSummary;
      })
      .then(setReviewSummary)
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Human review state could not be loaded.",
        ),
      );
  }, [session]);

  const links = useMemo(
    () => (index ? sectionLinks(index, selectedVolume) : []),
    [index, selectedVolume],
  );

  useEffect(() => {
    if (!index || links.length === 0) return;
    if (!links.some((candidate) => candidate.id === selectedSectionId)) {
      setSelectedSectionId(links[0]!.id);
    }
  }, [index, links, selectedSectionId]);

  useEffect(() => {
    if (!selectedSectionId) return;
    setSection(undefined);
    fetch(
      `/api/corpus/al-isabah/sections/${encodeURIComponent(selectedSectionId)}`,
      { credentials: "same-origin" },
    )
      .then(async (response) => {
        if (!response.ok)
          throw new Error("This reading section is not available.");
        return parseReviewCorpusSection(await response.json());
      })
      .then((nextSection) => {
        setSection(nextSection);
        const params = new URLSearchParams({
          volume: String(nextSection.volume),
          section: nextSection.id,
        });
        window.history.replaceState(
          null,
          "",
          `${window.location.pathname}?${params}${pendingAnchor ? `#${pendingAnchor}` : ""}`,
        );
      })
      .catch((caught) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "The reading section could not be loaded.",
        ),
      );
  }, [selectedSectionId]);

  useEffect(() => {
    if (!section || !pendingAnchor) return;
    document
      .getElementById(pendingAnchor)
      ?.scrollIntoView({ behavior: "smooth" });
    setPendingAnchor("");
  }, [pendingAnchor, section]);

  const searchResults = useMemo(() => {
    const normalized = normalizeHonorificSearch(query.trim());
    if (!normalized || !index) return [];
    return index.items
      .filter(
        (item) =>
          (
            item.searchText ??
            normalizeHonorificSearch(`${item.titleEn} ${item.titleAr}`)
          ).includes(normalized) ||
          String(item.printedEntryNumber ?? "").includes(normalized),
      )
      .slice(0, 50);
  }, [index, query]);

  const visibleItems = useMemo(
    () =>
      section?.items.filter(
        (item) =>
          !hideReviewed ||
          (reviewSummary?.items[item.id]?.approvalCount ?? 0) === 0,
      ) ?? [],
    [hideReviewed, reviewSummary, section],
  );

  const volumeCoverage = useMemo(
    () =>
      summary?.volumes.map((volume) => {
        const sourceCount = volume.sourceItemCount ?? volume.itemCount;
        const volumeItems =
          index?.items.filter((item) => item.volume === volume.number) ?? [];
        const reviewedCount = volumeItems.filter(
          (item) => (reviewSummary?.items[item.id]?.approvalCount ?? 0) > 0,
        ).length;
        return {
          ...volume,
          sourceCount,
          reviewedCount,
          translationPercent: coveragePercent(volume.itemCount, sourceCount),
          reviewPercent: coveragePercent(reviewedCount, volume.itemCount),
        };
      }) ?? [],
    [index, reviewSummary, summary],
  );

  function updateReviewState(itemId: string, state: TranslationReviewState) {
    setReviewSummary((current) => {
      const previousReviewed = (current?.items[itemId]?.approvalCount ?? 0) > 0;
      const nextReviewed = state.approvalCount > 0;
      return {
        corpusId: current?.corpusId ?? section?.corpusId ?? "",
        reviewedItems:
          (current?.reviewedItems ?? 0) +
          (nextReviewed ? 1 : 0) -
          (previousReviewed ? 1 : 0),
        items: { ...current?.items, [itemId]: state },
      };
    });
  }

  function openSection(sectionId: string, anchor = "") {
    const target = index?.items.find((item) => item.sectionId === sectionId);
    if (target) setSelectedVolume(target.volume);
    setPendingAnchor(anchor);
    setSelectedSectionId(sectionId);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <>
      {error && <p className="issue-banner">{error}</p>}
      {summary && (
        <section
          className="edition-overview"
          aria-labelledby="edition-map-title"
        >
          <div>
            <p className="eyebrow">Live edition coverage</p>
            <h2 id="edition-map-title">Coverage by source volume</h2>
            <p>
              Translation coverage follows the deployed, source-locked corpus.
              Human-review progress updates from current approvals. Select any
              available volume to begin reading.
            </p>
          </div>
          <div className="volume-shelf" aria-label="Live coverage by volume">
            {volumeCoverage.map((volume) => (
              <button
                type="button"
                className={selectedVolume === volume.number ? "selected" : ""}
                aria-pressed={selectedVolume === volume.number}
                aria-label={`Volume ${volume.number}: ${volume.itemCount.toLocaleString()} of ${volume.sourceCount.toLocaleString()} source entries translated; ${volume.reviewedCount.toLocaleString()} of ${volume.itemCount.toLocaleString()} translations human reviewed; ${coverageStateLabel(volume.availability)}`}
                disabled={volume.itemCount === 0}
                onClick={() => {
                  setSelectedVolume(volume.number);
                  setSelectedSectionId("");
                }}
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
              </button>
            ))}
          </div>
          <p className="edition-status">
            {summary.counts.translated.toLocaleString()} translated records ·{" "}
            {summary.counts.unresolvedItems.toLocaleString()} unresolved items ·{" "}
            {(
              reviewSummary?.reviewedItems ?? summary.counts.humanReviewed
            ).toLocaleString()}{" "}
            human reviewed
            {summary.counts.quarantined !== undefined &&
              !summary.exclusions &&
              ` · ${summary.counts.quarantined.toLocaleString()} records excluded from this edition`}
            {summary.exclusions &&
              summary.exclusions
                .contextualPassagesPendingPublicSourceAlignment > 0 &&
              ` · ${summary.exclusions.contextualPassagesPendingPublicSourceAlignment.toLocaleString()} contextual passages excluded pending public-source alignment`}
            {summary.exclusions &&
              summary.exclusions.recordsPendingRemediation > 0 &&
              ` · ${summary.exclusions.recordsPendingRemediation.toLocaleString()} records withheld for remediation`}
          </p>
        </section>
      )}

      {session === "anonymous" && (
        <details className="reviewer-invitation">
          <summary>Have an invitation to review or correct the text?</summary>
          <CorpusAccess siteKey={siteKey} returnTo="/works/al-isabah/" />
        </details>
      )}
      {session === "limited" && (
        <p className="issue-banner">
          @{identity?.login} can read the public working edition, but does not
          currently have access to submit reviews or corrections.
        </p>
      )}
      {index && (
        <section
          className="book-reader"
          aria-label="Al-Isabah working translation"
        >
          <aside className="reader-contents">
            <p className="eyebrow">Volume {selectedVolume}</p>
            <h2>Reading sections</h2>
            <ol>
              {links.map((link) => (
                <li key={link.id}>
                  <button
                    type="button"
                    className={selectedSectionId === link.id ? "selected" : ""}
                    onClick={() => openSection(link.id)}
                  >
                    <span>{link.label}</span>
                    <small>{link.itemCount} records</small>
                  </button>
                </li>
              ))}
            </ol>
            <details className="reader-index">
              <summary>Search the full edition</summary>
              <label>
                Name or entry number
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search all available volumes"
                />
              </label>
              {query && (
                <ol>
                  {searchResults.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => openSection(item.sectionId, item.id)}
                      >
                        <span>{item.titleEn}</span>
                        <small>
                          Volume {item.volume}
                          {item.printedPageStart !== null &&
                            ` · p. ${item.printedPageStart}`}
                        </small>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </details>
          </aside>

          <div className="reading-page">
            {!section && <p>Opening reading section…</p>}
            {section && (
              <>
                <header className="reading-section-header">
                  <p className="eyebrow">
                    Volume {section.volume} · section {section.position} of{" "}
                    {section.totalSections}
                  </p>
                  <h2>{section.label}</h2>
                  <p>
                    {section.availability === "complete_translation"
                      ? "Continuous working translation"
                      : "Selected translated passages; intervening text is not yet available"}
                  </p>
                </header>
                <div className="reader-review-filter">
                  <label className="choice">
                    <input
                      type="checkbox"
                      checked={hideReviewed}
                      onChange={(event) =>
                        setHideReviewed(event.target.checked)
                      }
                    />
                    Hide human-reviewed translations
                  </label>
                  <span>
                    Showing {visibleItems.length.toLocaleString()} of{" "}
                    {section.items.length.toLocaleString()} records in this
                    section
                  </span>
                </div>
                <div className="reading-flow">
                  {visibleItems.map((item) => (
                    <ReadingRecord
                      item={item}
                      reviewState={reviewSummary?.items[item.id]}
                      onReviewStateChange={(state) =>
                        updateReviewState(item.id, state)
                      }
                      reviewStateLoaded={reviewSummary !== undefined}
                      canReview={session === "active"}
                      key={item.id}
                    />
                  ))}
                  {visibleItems.length === 0 && (
                    <p className="empty-reading-state">
                      Every record in this section has a current human approval.
                      Show reviewed translations to read them again.
                    </p>
                  )}
                </div>
                {session === "active" && (
                  <SelectionReporter corpusId={section.corpusId} />
                )}
                <nav
                  className="section-pagination"
                  aria-label="Reading sections"
                >
                  <button
                    className="button secondary"
                    type="button"
                    disabled={!section.previousSectionId}
                    onClick={() =>
                      section.previousSectionId &&
                      openSection(section.previousSectionId)
                    }
                  >
                    Previous section
                  </button>
                  <span>
                    {section.position} / {section.totalSections}
                  </span>
                  <button
                    className="button secondary"
                    type="button"
                    disabled={!section.nextSectionId}
                    onClick={() =>
                      section.nextSectionId &&
                      openSection(section.nextSectionId)
                    }
                  >
                    Next section
                  </button>
                </nav>
              </>
            )}
          </div>
        </section>
      )}
    </>
  );
}

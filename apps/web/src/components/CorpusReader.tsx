import {
  parseReviewCorpusIndex,
  parseReviewCorpusSection,
  parseReviewCorpusSummary,
  type ReviewCorpusIndex,
  type ReviewCorpusItem,
  type ReviewCorpusSection,
  type ReviewCorpusSummary,
} from "@sabiqah/release-model";
import { useEffect, useMemo, useState } from "react";

import { CorpusAccess } from "./CorpusAccess";

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
                  {note.arabicSpan}
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
        Provenance <code>{item.provenance.sourceArtifactId}</code> · integrity{" "}
        <code>{item.provenance.sourceArtifactSha256}</code>
      </p>
    </details>
  );
}

function ReadingRecord({ item }: { item: ReviewCorpusItem }) {
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
          <h3>{item.title.en}</h3>
          <p lang="ar" dir="rtl">
            {item.title.ar}
          </p>
        </div>
      </header>
      {item.relationship && (
        <p className="passage-context">{item.relationship}</p>
      )}
      {item.segments.map((segment) => (
        <section className="reading-bilingual" key={segment.id}>
          <div lang="en" dir="ltr">
            <p className="corpus-text">
              {segment.english || "Translation not yet available."}
            </p>
          </div>
          <div lang="ar" dir="rtl">
            <p className="arabic corpus-text">{segment.arabic}</p>
          </div>
        </section>
      ))}
      <ReviewEvidence item={item} />
    </article>
  );
}

export function CorpusReader({ siteKey }: { siteKey?: string }) {
  const [summary, setSummary] = useState<ReviewCorpusSummary>();
  const [index, setIndex] = useState<ReviewCorpusIndex>();
  const [section, setSection] = useState<ReviewCorpusSection>();
  const [identity, setIdentity] = useState<SessionIdentity>();
  const [session, setSession] = useState<
    "loading" | "anonymous" | "active" | "limited"
  >("loading");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedVolume, setSelectedVolume] = useState(8);
  const [selectedSectionId, setSelectedSectionId] = useState("");
  const [pendingAnchor, setPendingAnchor] = useState("");

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
          throw new Error(
            "The protected table of contents could not be loaded.",
          );
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
    if (session !== "active" || !selectedSectionId) return;
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
  }, [selectedSectionId, session]);

  useEffect(() => {
    if (!section || !pendingAnchor) return;
    document
      .getElementById(pendingAnchor)
      ?.scrollIntoView({ behavior: "smooth" });
    setPendingAnchor("");
  }, [pendingAnchor, section]);

  const searchResults = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    if (!normalized || !index) return [];
    return index.items
      .filter(
        (item) =>
          item.titleEn.toLocaleLowerCase().includes(normalized) ||
          item.titleAr.includes(query.trim()) ||
          String(item.printedEntryNumber ?? "").includes(normalized),
      )
      .slice(0, 50);
  }, [index, query]);

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
            <p className="eyebrow">Available working edition</p>
            <h2 id="edition-map-title">Read by the book’s own volumes</h2>
            <p>
              Volume 8 is available as a complete working translation. Earlier
              volumes contain selected translated passages only; gaps are shown
              honestly rather than disguised as a complete text.
            </p>
          </div>
          <div className="volume-shelf" aria-label="Available volumes">
            {summary.volumes.map((volume) => (
              <button
                type="button"
                className={selectedVolume === volume.number ? "selected" : ""}
                onClick={() => {
                  setSelectedVolume(volume.number);
                  setSelectedSectionId("");
                }}
                disabled={session !== "active"}
                key={volume.id}
              >
                <strong>{volume.number}</strong>
                <span>{volume.itemCount.toLocaleString()} records</span>
                <small>
                  {volume.availability === "complete_translation"
                    ? "complete working translation"
                    : "selected passages"}
                </small>
              </button>
            ))}
          </div>
          <p className="edition-status">
            {summary.counts.translated.toLocaleString()} translated records ·{" "}
            {summary.counts.unresolvedItems.toLocaleString()} unresolved items ·{" "}
            {summary.counts.humanReviewed.toLocaleString()} human reviewed
          </p>
        </section>
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
      {session === "active" && index && (
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
                <div className="reading-flow">
                  {section.items.map((item) => (
                    <ReadingRecord item={item} key={item.id} />
                  ))}
                </div>
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

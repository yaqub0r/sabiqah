import { useEffect, useRef, useState } from "react";

interface SelectionDraft {
  corpusId: string;
  itemId: string;
  segmentId: string;
  field: "title" | "segment";
  language: "Arabic" | "English";
  selectedText: string;
  context: string;
  pageUrl: string;
  position: { left: number; top: number };
}

interface ReportTarget extends HTMLElement {
  dataset: DOMStringMap & {
    reportItemId: string;
    reportSegmentId: string;
    reportField: "title" | "segment";
    reportLanguage: "Arabic" | "English";
  };
}

const categories = [
  "formatting",
  "translation",
  "segmentation",
  "title",
  "honorific",
  "source structure",
];

const blockTextElements = new Set([
  "BLOCKQUOTE",
  "DIV",
  "FIGCAPTION",
  "FIGURE",
  "H1",
  "H2",
  "H3",
  "H4",
  "H5",
  "H6",
  "LI",
  "P",
  "SECTION",
]);

function renderedText(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
  const content = [...node.childNodes].map(renderedText).join("");
  return node instanceof Element && blockTextElements.has(node.tagName)
    ? ` ${content} `
    : content;
}

function targetFor(node: Node | null): ReportTarget | null {
  const element =
    node instanceof Element
      ? node
      : node?.parentElement instanceof Element
        ? node.parentElement
        : null;
  return element?.closest<ReportTarget>("[data-report-item-id]") ?? null;
}

export function draftFromSelection(
  selection: Selection | null,
  corpusId: string,
): SelectionDraft | null {
  if (!selection || selection.isCollapsed || selection.rangeCount !== 1)
    return null;
  const selectedText = selection.toString().normalize("NFC").trim();
  if (!selectedText || selectedText.length > 1_000) return null;
  const selectedCollapsed = selectedText.replace(/\s+/g, " ").trim();
  const candidates = [
    targetFor(selection.anchorNode),
    targetFor(selection.focusNode),
  ].filter(
    (candidate, index, values): candidate is ReportTarget =>
      candidate !== null && values.indexOf(candidate) === index,
  );
  const matches = candidates
    .map((target) => {
      const text = renderedText(target).replace(/\s+/g, " ").trim();
      return { target, text, offset: text.indexOf(selectedCollapsed) };
    })
    .filter(({ offset }) => offset >= 0);
  if (matches.length !== 1) return null;
  const [{ target: anchor, text: targetText, offset }] = matches;
  const start = Math.max(0, offset - 180);
  const end = Math.min(
    targetText.length,
    offset + selectedCollapsed.length + 180,
  );
  const rectangle = selection.getRangeAt(0).getBoundingClientRect();
  return {
    corpusId,
    itemId: anchor.dataset.reportItemId,
    segmentId: anchor.dataset.reportSegmentId,
    field: anchor.dataset.reportField,
    language: anchor.dataset.reportLanguage,
    selectedText,
    context: targetText.slice(start, end),
    pageUrl: `${window.location.pathname}${window.location.search}${window.location.hash}`,
    position: {
      left: Math.min(Math.max(12, rectangle.left), window.innerWidth - 190),
      top: Math.min(
        Math.max(12, rectangle.bottom + 8),
        window.innerHeight - 54,
      ),
    },
  };
}

export function SelectionReporter({ corpusId }: { corpusId: string }) {
  const [draft, setDraft] = useState<SelectionDraft | null>(null);
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState(categories[0]!);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [issue, setIssue] = useState<{ number: number; url: string } | null>(
    null,
  );
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const update = () => {
      if (open) return;
      setDraft(draftFromSelection(window.getSelection(), corpusId));
    };
    let pendingUpdate = 0;
    const updateAfterInput = () => {
      cancelAnimationFrame(pendingUpdate);
      pendingUpdate = requestAnimationFrame(update);
    };
    document.addEventListener("selectionchange", update);
    document.addEventListener("pointerup", updateAfterInput);
    document.addEventListener("keyup", updateAfterInput);
    return () => {
      cancelAnimationFrame(pendingUpdate);
      document.removeEventListener("selectionchange", update);
      document.removeEventListener("pointerup", updateAfterInput);
      document.removeEventListener("keyup", updateAfterInput);
    };
  }, [corpusId, open]);

  useEffect(() => {
    if (open) heading.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  function close() {
    setOpen(false);
    setDraft(null);
    setIssue(null);
    setError("");
    setComment("");
  }

  function beginReport() {
    if (!draft) return;
    setOpen(true);
    window.getSelection()?.removeAllRanges();
  }

  async function submit(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || !comment.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await fetch("/api/corpus/al-isabah/reports", {
        method: "POST",
        credentials: "same-origin",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...draft, category, comment: comment.trim() }),
      });
      const body = (await response.json().catch(() => null)) as {
        issue?: { number: number; url: string };
        error?: string;
      } | null;
      if (!response.ok || !body?.issue)
        throw new Error(body?.error ?? "The report could not be created.");
      setIssue(body.issue);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The report could not be created.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      {draft && !open && (
        <button
          className="selection-report-action"
          style={{ left: draft.position.left, top: draft.position.top }}
          type="button"
          onClick={beginReport}
        >
          Report selected text
        </button>
      )}
      {open && draft && (
        <div
          className="selection-report-backdrop"
          onMouseDown={(event) =>
            event.target === event.currentTarget && close()
          }
        >
          <section
            className="selection-report-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="selection-report-title"
          >
            <button
              className="selection-report-close"
              type="button"
              aria-label="Close report form"
              onClick={close}
            >
              ×
            </button>
            <p className="eyebrow">
              {draft.language} · {draft.field}
            </p>
            <h2 id="selection-report-title" tabIndex={-1} ref={heading}>
              Report selected text
            </h2>
            {issue ? (
              <div className="selection-report-success" role="status">
                <p>Your report is now visible for triage.</p>
                <a href={issue.url} target="_blank" rel="noreferrer">
                  Open GitHub issue #{issue.number}
                </a>
              </div>
            ) : (
              <form onSubmit={submit}>
                <blockquote
                  lang={draft.language === "Arabic" ? "ar" : "en"}
                  dir={draft.language === "Arabic" ? "rtl" : "ltr"}
                >
                  {draft.selectedText}
                </blockquote>
                <label>
                  Problem category
                  <select
                    value={category}
                    onChange={(event) => setCategory(event.target.value)}
                  >
                    {categories.map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  What should a maintainer know?
                  <textarea
                    required
                    maxLength={1_000}
                    rows={4}
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                  />
                </label>
                {error && (
                  <p className="form-error" role="alert">
                    {error}
                  </p>
                )}
                <div className="selection-report-buttons">
                  <button
                    className="button secondary"
                    type="button"
                    onClick={close}
                  >
                    Cancel
                  </button>
                  <button
                    className="button"
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting ? "Creating issue…" : "Create issue"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </>
  );
}

import { expandHonorifics } from "@sabiqah/release-model";

import {
  type CorpusContext,
  LEGACY_CORPUS_CONTEXT,
  corpusObjectKey,
} from "./corpus";

export const REPORT_CATEGORIES = [
  "formatting",
  "translation",
  "segmentation",
  "title",
  "honorific",
  "source structure",
] as const;

type ReportCategory = (typeof REPORT_CATEGORIES)[number];
type ReportLanguage = "Arabic" | "English";
type ReportField = "title" | "segment";

interface ReportRequest {
  corpusId: string;
  itemId: string;
  segmentId: string;
  field: ReportField;
  language: ReportLanguage;
  category: ReportCategory;
  selectedText: string;
  context: string;
  comment: string;
  pageUrl: string;
}

interface CorpusItem {
  corpusId: string;
  id: string;
  printedEntryNumber?: number | null;
  title: { ar: string; en: string };
  segments: Array<{
    id: string;
    arabic: string;
    english: string;
    pages: Array<{ printedPage: number | null }>;
  }>;
}

export interface ReportMember {
  github_login: string;
}

export class SelectionReportError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

const ITEM_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$/;

function boundedString(value: unknown, maximum: number): string | null {
  if (typeof value !== "string") return null;
  const normalized = value
    .normalize("NFC")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .trim();
  return normalized && normalized.length <= maximum ? normalized : null;
}

function collapsed(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function parseSelectionReport(
  value: unknown,
  corpusId = LEGACY_CORPUS_CONTEXT.id,
): ReportRequest | null {
  if (!value || typeof value !== "object") return null;
  const body = value as Record<string, unknown>;
  const itemId = boundedString(body.itemId, 200);
  const segmentId = boundedString(body.segmentId, 200);
  const selectedText = boundedString(body.selectedText, 1_000);
  const context = boundedString(body.context, 2_000);
  const comment = boundedString(body.comment, 1_000);
  const pageUrl = boundedString(body.pageUrl, 2_048);
  if (
    body.corpusId !== corpusId ||
    !itemId ||
    !ITEM_ID.test(itemId) ||
    !segmentId ||
    !ITEM_ID.test(segmentId) ||
    !selectedText ||
    !context ||
    !comment ||
    !pageUrl ||
    (body.field !== "title" && body.field !== "segment") ||
    (body.language !== "Arabic" && body.language !== "English") ||
    !REPORT_CATEGORIES.includes(body.category as ReportCategory)
  ) {
    return null;
  }
  return {
    corpusId,
    itemId,
    segmentId,
    field: body.field,
    language: body.language,
    category: body.category as ReportCategory,
    selectedText,
    context,
    comment,
    pageUrl,
  };
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function validatePageUrl(value: string, requestUrl: string): string {
  const request = new URL(requestUrl);
  const page = new URL(value, request.origin);
  if (page.origin !== request.origin || page.pathname !== "/works/al-isabah/")
    throw new SelectionReportError("Invalid reader URL", 400);
  page.username = "";
  page.password = "";
  return page.toString();
}

function pagesFor(item: CorpusItem, segmentId: string): string {
  const pages = item.segments
    .filter((segment) => segmentId === "title" || segment.id === segmentId)
    .flatMap((segment) => segment.pages.map((page) => page.printedPage))
    .filter((page): page is number => page !== null);
  return [...new Set(pages)].join("–") || "not recorded";
}

function canonicalText(item: CorpusItem, report: ReportRequest): string | null {
  if (report.field === "title") {
    if (report.segmentId !== "title") return null;
    return report.language === "Arabic" ? item.title.ar : item.title.en;
  }
  const segment = item.segments.find(({ id }) => id === report.segmentId);
  if (!segment) return null;
  return report.language === "Arabic" ? segment.arabic : segment.english;
}

export async function createSelectionReport(
  bucket: R2Bucket,
  corpus: CorpusContext,
  githubToken: string | undefined,
  member: ReportMember,
  value: unknown,
  requestUrl: string,
  githubFetch: typeof fetch = fetch,
): Promise<{ number: number; url: string }> {
  if (!githubToken)
    throw new SelectionReportError(
      "Selection reporting is not configured",
      503,
    );
  const report = parseSelectionReport(value, corpus.id);
  if (!report) throw new SelectionReportError("Invalid report", 400);

  const object = await bucket.get(
    corpusObjectKey(corpus, "item", report.itemId),
  );
  if (!object) throw new SelectionReportError("Corpus item not found", 404);
  const item = (await object.json()) as CorpusItem;
  if (item.corpusId !== corpus.id || item.id !== report.itemId)
    throw new SelectionReportError("Corpus item is inconsistent", 409);

  const sourceText = canonicalText(item, report);
  if (!sourceText)
    throw new SelectionReportError("Report target not found", 404);
  const source = collapsed(
    expandHonorifics(sourceText, report.language === "English" ? "en" : "ar"),
  );
  const selected = collapsed(report.selectedText);
  const context = collapsed(report.context);
  if (
    !source.includes(selected) ||
    !source.includes(context) ||
    !context.includes(selected)
  )
    throw new SelectionReportError("Selected text is stale or invalid", 409);

  const pageUrl = validatePageUrl(report.pageUrl, requestUrl);
  const entry = item.printedEntryNumber ?? report.itemId;
  const title = `[${report.category}] Al-Isabah entry ${entry}`;
  const body = [
    "## Reader text report",
    "",
    `- **Entry:** ${escapeHtml(String(entry))}`,
    `- **Printed page:** ${escapeHtml(pagesFor(item, report.segmentId))}`,
    `- **Side:** ${report.language}`,
    `- **Field:** ${report.field}`,
    `- **Record ID:** <code>${escapeHtml(report.itemId)}</code>`,
    `- **Segment ID:** <code>${escapeHtml(report.segmentId)}</code>`,
    `- **Corpus:** <code>${escapeHtml(corpus.id)}</code>`,
    `- **Reporter:** @${escapeHtml(member.github_login)}`,
    `- **Reader URL:** ${escapeHtml(pageUrl)}`,
    "",
    "### Selected text",
    `<pre>${escapeHtml(report.selectedText)}</pre>`,
    "",
    "### Surrounding context",
    `<pre>${escapeHtml(report.context)}</pre>`,
    "",
    "### Reporter comment",
    `<pre>${escapeHtml(report.comment)}</pre>`,
    "",
    "_This is unadjudicated workflow evidence. It does not change or approve canonical book content._",
  ].join("\n");

  const response = await githubFetch(
    "https://api.github.com/repos/yaqub0r/sabiqah/issues",
    {
      method: "POST",
      headers: {
        accept: "application/vnd.github+json",
        authorization: `Bearer ${githubToken}`,
        "content-type": "application/json",
        "user-agent": "sabiqah-platform-worker",
        "x-github-api-version": "2022-11-28",
      },
      body: JSON.stringify({ title, body }),
    },
  );
  if (!response.ok)
    throw new SelectionReportError("GitHub issue creation failed", 502);
  const result = (await response.json()) as {
    number?: unknown;
    html_url?: unknown;
  };
  if (typeof result.number !== "number" || typeof result.html_url !== "string")
    throw new SelectionReportError("GitHub returned an invalid issue", 502);
  return { number: result.number, url: result.html_url };
}

import { z } from "zod";

export * from "./reviewCorpus";
export * from "./honorifics";

const identifier = z
  .string()
  .min(3)
  .max(160)
  .regex(/^[a-z0-9][a-z0-9._-]+$/);

export const sourceSpanSchema = z
  .object({
    id: identifier,
    editionId: identifier,
    volume: z.string().min(1),
    pageStart: z.string().min(1),
    pageEnd: z.string().min(1).optional(),
    evidenceRefs: z.array(z.string().min(1)).min(1),
  })
  .strict();

export const segmentSchema = z
  .object({
    id: identifier,
    arabic: z
      .object({
        text: z.string().min(1),
        reviewState: z.enum(["unreviewed", "reviewed", "verified", "disputed"]),
      })
      .strict(),
    english: z
      .object({
        text: z.string(),
        reviewState: z.enum([
          "untranslated",
          "draft",
          "reviewed",
          "verified",
          "disputed",
        ]),
      })
      .strict(),
    sourceSpanRefs: z.array(identifier).min(1),
    notes: z.array(z.string().min(1)).optional(),
  })
  .strict();

export const entryIssueSchema = z
  .object({
    code: identifier,
    severity: z.enum(["notice", "warning", "blocking"]),
    summary: z.string().min(1),
    segmentIds: z.array(identifier).min(1),
  })
  .strict();

export const bookEntrySchema = z
  .object({
    id: identifier,
    sequence: z.number().int().positive(),
    title: z.object({ ar: z.string().min(1), en: z.string().min(1) }).strict(),
    sourceSpans: z.array(sourceSpanSchema).min(1),
    segments: z.array(segmentSchema).min(1),
    issues: z.array(entryIssueSchema),
  })
  .strict()
  .superRefine((entry, context) => {
    const spanIds = new Set(entry.sourceSpans.map((span) => span.id));
    const segmentIds = new Set(entry.segments.map((segment) => segment.id));

    for (const segment of entry.segments) {
      for (const reference of segment.sourceSpanRefs) {
        if (!spanIds.has(reference)) {
          context.addIssue({
            code: "custom",
            message: `Segment ${segment.id} references unknown source span ${reference}`,
          });
        }
      }
    }

    for (const issue of entry.issues) {
      for (const segmentId of issue.segmentIds) {
        if (!segmentIds.has(segmentId)) {
          context.addIssue({
            code: "custom",
            message: `Issue ${issue.code} references unknown segment ${segmentId}`,
          });
        }
      }
    }
  });

export const bookReleaseSchema = z
  .object({
    schemaVersion: z.literal("1.0.0"),
    work: z
      .object({
        slug: identifier,
        titleAr: z.string().min(1),
        titleEn: z.string().min(1),
      })
      .strict(),
    release: z
      .object({
        id: identifier,
        publishedAt: z.iso.datetime(),
        sourceCommit: z.string().regex(/^[a-f0-9]{40}$/),
        repositoryUrl: z.url(),
      })
      .strict(),
    entries: z.array(bookEntrySchema).min(1),
  })
  .strict();

export const proposalOperationSchema = z
  .object({
    segmentId: identifier,
    target: z.enum(["translation", "canonical_arabic"]),
    proposedText: z.string().min(1),
    rationale: z.string(),
    evidenceRefs: z.array(z.string().min(1)),
  })
  .strict()
  .superRefine((operation, context) => {
    if (operation.target === "canonical_arabic") {
      if (operation.rationale.trim().length < 10) {
        context.addIssue({
          code: "custom",
          message: "Arabic corrections require a rationale.",
        });
      }
      if (operation.evidenceRefs.length === 0) {
        context.addIssue({
          code: "custom",
          message: "Arabic corrections require evidence.",
        });
      }
    }
  });

export const reviewProposalSchema = z
  .object({
    proposalVersion: z.literal("1.0.0"),
    bookSlug: identifier,
    baseReleaseId: identifier,
    entryId: identifier,
    createdAt: z.iso.datetime(),
    operations: z.array(proposalOperationSchema).min(1),
  })
  .strict();

export type BookRelease = z.infer<typeof bookReleaseSchema>;
export type BookEntry = z.infer<typeof bookEntrySchema>;
export type Segment = z.infer<typeof segmentSchema>;
export type ReviewProposal = z.infer<typeof reviewProposalSchema>;

export function parseBookRelease(value: unknown): BookRelease {
  return bookReleaseSchema.parse(value);
}

export function parseReviewProposal(value: unknown): ReviewProposal {
  return reviewProposalSchema.parse(value);
}

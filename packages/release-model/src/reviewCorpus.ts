import { z } from "zod";

const identifier = z
  .string()
  .min(3)
  .max(200)
  .regex(/^[A-Za-z0-9][A-Za-z0-9._:-]+$/);

export const reviewStateSchema = z.enum([
  "untranslated",
  "draft",
  "translated",
  "unreviewed",
  "in_review",
  "reviewed",
  "verified",
  "disputed",
  "needs_attention",
]);

export const reviewCorpusSummarySchema = z
  .object({
    schemaVersion: z.literal("1.0.0"),
    work: z
      .object({
        slug: z.literal("al-isabah"),
        titleAr: z.string().min(1),
        titleEn: z.string().min(1),
      })
      .strict(),
    corpus: z
      .object({
        id: identifier,
        sourceRepository: z.url(),
        sourceCommit: z.string().regex(/^[a-f0-9]{40}$/),
        generatedAt: z.iso.datetime(),
        promotionStatus: z.literal("blocked"),
      })
      .strict(),
    counts: z
      .object({
        entries: z.number().int().nonnegative(),
        contextualPassages: z.number().int().nonnegative(),
        translated: z.number().int().nonnegative(),
        needsAttention: z.number().int().nonnegative(),
        unresolvedItems: z.number().int().nonnegative(),
        humanReviewed: z.number().int().nonnegative(),
      })
      .strict(),
    collections: z
      .array(
        z
          .object({
            id: identifier,
            title: z.string().min(1),
            kind: z.enum(["volume", "cohort"]),
            itemCount: z.number().int().nonnegative(),
            reviewState: reviewStateSchema,
            description: z.string().min(1),
          })
          .strict(),
      )
      .min(1),
    coverage: z
      .object({
        sourceResults: z.number().int().nonnegative(),
        decisions: z.record(z.string(), z.number().int().nonnegative()),
      })
      .strict()
      .optional(),
  })
  .strict();

export const reviewCorpusListItemSchema = z
  .object({
    id: identifier,
    kind: z.enum(["entry", "context"]),
    sequence: z.number().int().nonnegative(),
    printedEntryNumber: z.number().int().positive().nullable(),
    volume: z.string().min(1),
    titleEn: z.string().min(1),
    titleAr: z.string(),
    translationState: reviewStateSchema,
    machineAssessment: z.enum(["pending", "passed", "needs_attention"]),
    humanReview: reviewStateSchema,
    unresolvedCount: z.number().int().nonnegative(),
    collectionIds: z.array(identifier).min(1),
    relationship: z.string().optional(),
  })
  .strict();

export const reviewCorpusIndexSchema = z
  .object({
    schemaVersion: z.literal("1.0.0"),
    corpusId: identifier,
    items: z.array(reviewCorpusListItemSchema),
  })
  .strict();

const corpusNameSchema = z
  .object({
    arabic: z.string(),
    english: z.string(),
    kind: z.string().min(1),
  })
  .strict();

const corpusUnresolvedSchema = z
  .object({
    category: z.string().min(1),
    arabicSpan: z.string().optional(),
    explanation: z.string().min(1),
    priority: z.string().optional(),
  })
  .strict();

export const reviewCorpusItemSchema = z
  .object({
    schemaVersion: z.literal("1.0.0"),
    corpusId: identifier,
    id: identifier,
    kind: z.enum(["entry", "context"]),
    sequence: z.number().int().nonnegative(),
    printedEntryNumber: z.number().int().positive().nullable(),
    volume: z.string().min(1),
    title: z.object({ en: z.string().min(1), ar: z.string() }).strict(),
    relationship: z.string().optional(),
    rationale: z.string().optional(),
    translationState: reviewStateSchema,
    machineAssessment: z.enum(["pending", "passed", "needs_attention"]),
    humanReview: reviewStateSchema,
    collectionIds: z.array(identifier).min(1),
    segments: z
      .array(
        z
          .object({
            id: identifier,
            arabic: z.string(),
            english: z.string(),
            pages: z.array(
              z
                .object({
                  volume: z.string().min(1),
                  printedPage: z.number().int().nonnegative().nullable(),
                  readerPage: z.number().int().nonnegative().nullable(),
                  providerPage: z.url().nullable(),
                })
                .strict(),
            ),
            machineState: z.string().min(1),
          })
          .strict(),
      )
      .min(1),
    names: z.array(corpusNameSchema),
    unresolved: z.array(corpusUnresolvedSchema),
    decisions: z
      .array(
        z
          .object({
            issue: z.string().min(1),
            resolution: z.string().min(1),
            basis: z.string().min(1),
          })
          .strict(),
      )
      .optional(),
    workflowStages: z
      .array(
        z
          .object({
            stage: z.enum([
              "source_alignment",
              "blind_translation",
              "critique",
              "adjudication",
              "machine_validation",
              "human_review",
              "compliance_promotion",
            ]),
            state: z.enum([
              "complete",
              "needs_attention",
              "pending",
              "blocked",
            ]),
            summary: z.string().min(1),
            englishText: z.string().optional(),
            issues: z
              .array(
                z
                  .object({
                    severity: z.string().min(1),
                    category: z.string().min(1),
                    explanation: z.string().min(1),
                    suggestedFix: z.string().optional(),
                  })
                  .strict(),
              )
              .optional(),
          })
          .strict(),
      )
      .min(1),
    provenance: z
      .object({
        sourceArtifactId: z.string().min(1),
        sourceArtifactSha256: z.string().regex(/^[a-f0-9]{64}$/),
      })
      .strict(),
  })
  .strict();

export type ReviewCorpusSummary = z.infer<typeof reviewCorpusSummarySchema>;
export type ReviewCorpusListItem = z.infer<typeof reviewCorpusListItemSchema>;
export type ReviewCorpusIndex = z.infer<typeof reviewCorpusIndexSchema>;
export type ReviewCorpusItem = z.infer<typeof reviewCorpusItemSchema>;

export function parseReviewCorpusSummary(value: unknown): ReviewCorpusSummary {
  return reviewCorpusSummarySchema.parse(value);
}

export function parseReviewCorpusIndex(value: unknown): ReviewCorpusIndex {
  return reviewCorpusIndexSchema.parse(value);
}

export function parseReviewCorpusItem(value: unknown): ReviewCorpusItem {
  return reviewCorpusItemSchema.parse(value);
}

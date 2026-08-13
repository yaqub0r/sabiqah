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

const availabilitySchema = z.enum([
  "complete_translation",
  "selected_passages",
]);

const volumeSchema = z
  .object({
    id: identifier,
    number: z.number().int().positive(),
    label: z.string().min(1),
    availability: availabilitySchema,
    itemCount: z.number().int().nonnegative(),
    sectionCount: z.number().int().positive(),
    firstPrintedPage: z.number().int().nonnegative().nullable(),
    lastPrintedPage: z.number().int().nonnegative().nullable(),
    description: z.string().min(1),
  })
  .strict();

export const reviewCorpusSummarySchema = z
  .object({
    schemaVersion: z.enum(["2.0.0", "3.0.0", "4.0.0"]),
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
        sourceAuthorityId: identifier.optional(),
        sourceArtifactSha256: z
          .string()
          .regex(/^[a-f0-9]{64}$/)
          .optional(),
        publicationStatus: z.literal("public-working").optional(),
        license: z
          .object({ spdx: z.string().min(1), url: z.url() })
          .strict()
          .optional(),
      })
      .strict(),
    counts: z
      .object({
        entries: z.number().int().nonnegative(),
        passages: z.number().int().nonnegative(),
        translated: z.number().int().nonnegative(),
        needsAttention: z.number().int().nonnegative(),
        unresolvedItems: z.number().int().nonnegative(),
        humanReviewed: z.number().int().nonnegative(),
        sourceInventory: z.number().int().nonnegative().optional(),
        quarantined: z.number().int().nonnegative().optional(),
      })
      .strict(),
    volumes: z.array(volumeSchema).min(1),
  })
  .strict();

export const reviewCorpusListItemSchema = z
  .object({
    id: identifier,
    kind: z.enum(["entry", "passage"]),
    sequence: z.number().int().nonnegative(),
    printedEntryNumber: z.number().int().positive().nullable(),
    sourceEntryNumber: z.number().int().positive().optional(),
    volume: z.number().int().positive(),
    printedPageStart: z.number().int().nonnegative().nullable(),
    printedPageEnd: z.number().int().nonnegative().nullable(),
    sectionId: identifier,
    titleEn: z.string().min(1),
    titleAr: z.string(),
    translationState: reviewStateSchema,
    machineAssessment: z.enum(["pending", "passed", "needs_attention"]),
    humanReview: reviewStateSchema,
    unresolvedCount: z.number().int().nonnegative(),
    publicEligibility: z.literal("eligible").optional(),
    relationship: z.string().optional(),
    searchText: z.string().optional(),
  })
  .strict();

export const reviewCorpusIndexSchema = z
  .object({
    schemaVersion: z.enum(["2.0.0", "3.0.0", "4.0.0"]),
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

const honorificOccurrenceSchema = z
  .object({
    id: identifier,
    semanticId: identifier,
    semanticClass: z.string().min(1),
    language: z.enum(["ar", "en", "ur"]),
    field: z.enum(["title", "segment"]),
    segmentId: identifier.optional(),
    observedForm: z.string().min(1),
    renderedForm: z.string().min(1),
    expandedArabic: z.string().min(1),
    accessibleText: z.string().min(1),
    formulaRole: z.enum(["formulaic", "substantive", "uncertain"]),
    referent: z
      .object({
        kind: z.string().min(1),
        scope: z.string().min(1),
        context: z.string(),
        status: z.enum(["machine-inferred", "human-reviewed", "unresolved"]),
      })
      .strict(),
    agreement: z
      .object({
        number: z.enum(["singular", "dual", "plural", "not-applicable"]),
        gender: z.enum([
          "masculine",
          "feminine",
          "masculine-or-mixed",
          "mixed",
          "common",
          "not-applicable",
        ]),
      })
      .strict(),
    familyIncluded: z.boolean(),
  })
  .strict();

export const reviewCorpusItemSchema = z
  .object({
    schemaVersion: z.enum(["2.0.0", "3.0.0", "4.0.0"]),
    corpusId: identifier,
    id: identifier,
    kind: z.enum(["entry", "passage"]),
    sequence: z.number().int().nonnegative(),
    printedEntryNumber: z.number().int().positive().nullable(),
    sourceEntryNumber: z.number().int().positive().optional(),
    volume: z.number().int().positive(),
    title: z.object({ en: z.string().min(1), ar: z.string() }).strict(),
    relationship: z.string().optional(),
    rationale: z.string().optional(),
    translationState: reviewStateSchema,
    machineAssessment: z.enum(["pending", "passed", "needs_attention"]),
    humanReview: reviewStateSchema,
    publicEligibility: z.literal("eligible").optional(),
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
                  volume: z.number().int().positive(),
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
    honorificPolicyVersion: z.string().optional(),
    honorifics: z.array(honorificOccurrenceSchema).optional(),
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
    source: z
      .object({
        authorityId: identifier,
        entryNumber: z.number().int().positive(),
        pages: z.array(z.string().regex(/^V\d{2}P\d{3}$/)),
        sourceTextSha256: z.string().regex(/^[a-f0-9]{64}$/),
        sourceExactTextSha256: z
          .string()
          .regex(/^[a-f0-9]{64}$/)
          .optional(),
        sourceUrl: z.url(),
        license: z.object({ spdx: z.string().min(1), url: z.url() }).strict(),
        alignment: z
          .object({
            method: z.string().min(1),
            titleScore: z.number().min(0).max(1),
            bodyScore: z.number().min(0).max(1),
          })
          .strict(),
      })
      .strict()
      .optional(),
    remediation: z
      .object({
        legacyAllocationNumber: z.number().int().positive(),
        sourceArabicReplaced: z.literal(true),
        privateLocatorsRemoved: z.literal(true),
        honorificInventory: z.record(
          z.string(),
          z.number().int().nonnegative(),
        ),
        honorificTypeCorrections: z.number().int().nonnegative(),
        sourceHonorificSemantics: z
          .record(z.string(), z.number().int().nonnegative())
          .optional(),
        englishHonorificSemantics: z
          .record(z.string(), z.number().int().nonnegative())
          .optional(),
        honorificLiteralInventoryDiffers: z.boolean().optional(),
        honorificSemanticReview: z
          .enum(["passed", "needs_attention"])
          .optional(),
        honorificFindings: z.array(z.string().min(1)).optional(),
        englishExcluded: z.boolean().optional(),
        englishExclusionReasonCodes: z.array(z.string().min(1)).optional(),
        removedApparatusParagraphs: z.number().int().nonnegative(),
        removedEditorialNotes: z.number().int().nonnegative(),
      })
      .strict()
      .optional(),
    provenance: z.union([
      z
        .object({
          sourceArtifactId: z.string().min(1),
          sourceArtifactSha256: z.string().regex(/^[a-f0-9]{64}$/),
        })
        .strict(),
      z
        .object({
          sourceAuthorityId: identifier,
          sourceArtifactSha256: z.string().regex(/^[a-f0-9]{64}$/),
          sourceTextSha256: z.string().regex(/^[a-f0-9]{64}$/),
          sourceExactTextSha256: z
            .string()
            .regex(/^[a-f0-9]{64}$/)
            .optional(),
        })
        .strict(),
    ]),
  })
  .strict()
  .superRefine((item, context) => {
    if (item.schemaVersion !== "4.0.0") return;
    if (!item.honorificPolicyVersion || !item.honorifics) {
      context.addIssue({
        code: "custom",
        message: "Schema 4.0.0 items require honorific policy metadata.",
      });
    }
    if (
      !item.source?.sourceExactTextSha256 ||
      !("sourceExactTextSha256" in item.provenance) ||
      !item.provenance.sourceExactTextSha256
    ) {
      context.addIssue({
        code: "custom",
        message: "Schema 4.0.0 items require exact-source integrity metadata.",
      });
    }
  });

export const reviewCorpusSectionSchema = z
  .object({
    schemaVersion: z.enum(["2.0.0", "3.0.0", "4.0.0"]),
    corpusId: identifier,
    id: identifier,
    volume: z.number().int().positive(),
    label: z.string().min(1),
    availability: availabilitySchema,
    position: z.number().int().positive(),
    totalSections: z.number().int().positive(),
    printedPageStart: z.number().int().nonnegative().nullable(),
    printedPageEnd: z.number().int().nonnegative().nullable(),
    previousSectionId: identifier.nullable(),
    nextSectionId: identifier.nullable(),
    items: z.array(reviewCorpusItemSchema).min(1),
  })
  .strict();

export type ReviewCorpusSummary = z.infer<typeof reviewCorpusSummarySchema>;
export type ReviewCorpusListItem = z.infer<typeof reviewCorpusListItemSchema>;
export type ReviewCorpusIndex = z.infer<typeof reviewCorpusIndexSchema>;
export type ReviewCorpusItem = z.infer<typeof reviewCorpusItemSchema>;
export type ReviewCorpusSection = z.infer<typeof reviewCorpusSectionSchema>;

export function parseReviewCorpusSummary(value: unknown): ReviewCorpusSummary {
  return reviewCorpusSummarySchema.parse(value);
}

export function parseReviewCorpusIndex(value: unknown): ReviewCorpusIndex {
  return reviewCorpusIndexSchema.parse(value);
}

export function parseReviewCorpusItem(value: unknown): ReviewCorpusItem {
  return reviewCorpusItemSchema.parse(value);
}

export function parseReviewCorpusSection(value: unknown): ReviewCorpusSection {
  return reviewCorpusSectionSchema.parse(value);
}

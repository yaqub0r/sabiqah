import verifiedRelease from "../../../../.runtime/bukhari-reader.json";

export interface BukhariRecord {
  sourceUnitId: string;
  sourceOrdinal: number;
  bookSection: "opening" | "faith";
  printedHadithNumber: number | null;
  kind: string;
  arabic: string;
  english: string;
  humanReview: "unreviewed";
  segments: { start: number; end: number; kind: string; arabic: string }[];
  uncertainties: {
    category: string;
    reportId: string | null;
    summary: string;
  }[];
  isnad: {
    status: string;
    note: string;
    nodes: {
      id: string;
      arabic: string | null;
      kind: string;
      status: string;
      note: string;
    }[];
    edges: {
      id: string;
      from: string;
      to: string;
      mode: string;
      note: string;
      arabicWording: string | null;
    }[];
    paths: {
      id: string;
      kind: string;
      status: string;
      nodeIds: string[];
      edgeIds: string[];
      note: string;
    }[];
    reports: {
      id: string;
      start: number;
      end: number;
      status: string;
      pathIds: string[];
      note: string;
    }[];
  };
}

// Generated only by the fail-closed verifier before Astro starts. Never served
// directly or sourced from a mutable upstream working tree.
export const bukhari = verifiedRelease as {
  records: BukhariRecord[];
  releaseUrl: string;
  manifest: {
    releaseId: string;
    repositoryCommit: string;
    proposal: {
      rights: {
        attribution: string;
        arabicBasis: string;
        residualRisk: string;
        excludedMaterial: string[];
      };
      sourceAuthority: { edition: string; limitations: string[] };
    };
  };
};

export const bukhariSections = [
  { id: "opening", title: "Beginning of Revelation", range: "Reports 1–7" },
  { id: "faith", title: "Book of Faith", range: "Reports 8–58" },
] as const;

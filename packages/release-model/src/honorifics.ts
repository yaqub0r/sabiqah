import formulaProjection from "./al-isabah-honorifics.projection.json";
import registry from "./honorifics.presentation.json";

export type HonorificLanguage = "ar" | "en" | "ur";

export type HonorificAgreement = {
  number: "singular" | "dual" | "plural" | "not-applicable";
  gender:
    | "masculine"
    | "feminine"
    | "masculine-or-mixed"
    | "mixed"
    | "common"
    | "not-applicable";
};

export type HonorificEntry = {
  id: string;
  semanticClass: string;
  expandedArabic: string;
  accessibleEnglish: string;
  compactCharacter: string;
  codePoint: string;
  unicodeVersion: string;
  fontSupport: "supported" | "fallback-expanded";
  referent: { kind: string; scope: string };
  agreement: HonorificAgreement;
  familyIncluded: boolean;
  alternateCharacters: string[];
  arabicAliases: string[];
  englishAliases: string[];
};

export type AlIsabahFormulaProjectionEntry = {
  source: string;
  target: string;
  semanticClass: string;
  referentScope: string;
  grammaticalAgreement: string;
  expandedArabic: string;
  accessibleEnglish: string;
};

export const honorificRegistry = registry as {
  schema: "sabiqah.honorific-presentation.v1";
  role: "consumer-presentation-only";
  governanceNotice: string;
  schemaVersion: string;
  unicodeVersion: string;
  fontBaseline: {
    family: string;
    version: string;
    package: string;
    packageVersion: string;
    arabicWoff2Sha256: string;
    compactThroughUnicode: string;
  };
  entries: HonorificEntry[];
};

export const alIsabahFormulaProjection = formulaProjection as {
  schema: "sabiqah.al-isabah-honorific-projection.v1";
  role: "verified-consumer-projection";
  source: {
    repository: string;
    commit: string;
    referencePath: string;
    referenceVersion: string;
    referenceSha256: string;
    artifactPath: string;
    artifactVersion: string;
    artifactSha256: string;
    textNormalization: "utf-8-lf";
  };
  entries: AlIsabahFormulaProjectionEntry[];
};

const projectedFormulaByTarget = new Map<
  string,
  AlIsabahFormulaProjectionEntry
>();
for (const formula of alIsabahFormulaProjection.entries) {
  if ([...formula.target].length !== 1) continue;
  const existing = projectedFormulaByTarget.get(formula.target);
  if (
    existing &&
    (existing.semanticClass !== formula.semanticClass ||
      existing.grammaticalAgreement !== formula.grammaticalAgreement)
  ) {
    throw new Error(
      `Conflicting Al-Isabah formula semantics for ${formula.target}`,
    );
  }
  projectedFormulaByTarget.set(formula.target, formula);
}

export const honorificEntries = honorificRegistry.entries.map((entry) => {
  const formula = projectedFormulaByTarget.get(entry.compactCharacter);
  if (!formula) return entry;
  return {
    ...entry,
    semanticClass: formula.semanticClass,
    referent: { ...entry.referent, scope: formula.referentScope },
    agreement: projectedAgreement(formula.grammaticalAgreement),
    familyIncluded: formula.semanticClass.includes("family"),
  } satisfies HonorificEntry;
});

function projectedAgreement(value: string): HonorificAgreement {
  const agreements: Record<string, HonorificAgreement> = {
    "masculine singular and masculine plural": {
      number: "plural",
      gender: "masculine-or-mixed",
    },
    "masculine singular with family inclusion": {
      number: "plural",
      gender: "mixed",
    },
    "masculine singular": { number: "singular", gender: "masculine" },
    "feminine singular": { number: "singular", gender: "feminine" },
    dual: { number: "dual", gender: "common" },
    "masculine plural": {
      number: "plural",
      gender: "masculine-or-mixed",
    },
    "feminine plural": { number: "plural", gender: "feminine" },
    plural: { number: "plural", gender: "masculine-or-mixed" },
    not_applicable: {
      number: "not-applicable",
      gender: "not-applicable",
    },
  };
  const agreement = agreements[value];
  if (!agreement) throw new Error(`Unknown Al-Isabah agreement: ${value}`);
  return agreement;
}

const byCharacter = new Map<string, HonorificEntry>();
for (const entry of honorificEntries) {
  byCharacter.set(entry.compactCharacter, entry);
  for (const alternate of entry.alternateCharacters) {
    byCharacter.set(alternate, entry);
  }
}

const upstreamArabicCompactions = alIsabahFormulaProjection.entries
  .filter(({ target }) => [...target].length === 1 && byCharacter.has(target))
  .sort((left, right) => right.source.length - left.source.length);

const honorificCharacterPattern = new RegExp(
  `(${[...byCharacter.keys()]
    .sort((left, right) => right.length - left.length)
    .map(escapeRegExp)
    .join("|")})`,
  "gu",
);

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function replaceAliases(
  value: string,
  language: HonorificLanguage,
  aliases: (entry: HonorificEntry) => string[],
): string {
  const grouped = new Map<
    string,
    Array<{ alias: string; entry: HonorificEntry }>
  >();
  for (const entry of honorificEntries) {
    for (const alias of aliases(entry)) {
      const lookup = language === "en" ? alias.toLocaleLowerCase() : alias;
      grouped.set(lookup, [...(grouped.get(lookup) ?? []), { alias, entry }]);
    }
  }
  const replacements = new Map<
    string,
    { alias: string; entry: HonorificEntry }
  >();
  for (const [lookup, candidates] of grouped) {
    const semanticKeys = new Set(
      candidates.map(({ entry }) =>
        [
          entry.semanticClass,
          entry.agreement.number,
          entry.agreement.gender,
          entry.familyIncluded ? "family" : "no-family",
        ].join("|"),
      ),
    );
    if (semanticKeys.size > 1) continue;
    replacements.set(
      lookup,
      candidates.find(({ entry }) => entry.fontSupport === "supported") ??
        candidates[0],
    );
  }
  const aliasesPattern = [...replacements.values()]
    .sort((left, right) => right.alias.length - left.alias.length)
    .map(({ alias }) => escapeRegExp(alias))
    .join("|");
  const pattern = new RegExp(
    language === "en"
      ? `(,[\\t ]*)?(${aliasesPattern})([\\t ]*,)?`
      : `(${aliasesPattern})`,
    language === "en" ? "giu" : "gu",
  );
  return value.replace(pattern, (_matched, first, second, third) => {
    const matchedAlias = language === "en" ? second : first;
    const lookup =
      language === "en" ? matchedAlias.toLocaleLowerCase() : matchedAlias;
    const { entry } = replacements.get(lookup)!;
    const fallback =
      language === "en" ? entry.accessibleEnglish : entry.expandedArabic;
    let replacement =
      entry.fontSupport === "supported" ? entry.compactCharacter : fallback;
    const divineName =
      language === "en" &&
      entry.semanticClass.replaceAll("_", "-") === "divine-exaltation"
        ? /^(Allah|God)\b/i.exec(matchedAlias)?.[1]
        : undefined;
    if (divineName) replacement = `${divineName} ${replacement}`;
    if (language === "en" && first) {
      // Expanded English honorifics are often parenthetical. Once compacted,
      // the glyph attaches directly to its referent, so the opening comma and
      // its paired closing comma no longer belong in the sentence.
      return ` ${replacement}`;
    }
    if (language === "en") return `${replacement}${third ?? ""}`;
    return replacement;
  });
}

export function findHonorificByCharacter(
  character: string,
): HonorificEntry | undefined {
  return byCharacter.get(character);
}

export function tokenizeHonorifics(
  value: string,
): Array<string | HonorificEntry> {
  if (!value) return [value];
  return value
    .split(honorificCharacterPattern)
    .filter(Boolean)
    .map((part) => byCharacter.get(part) ?? part);
}

export function compactHonorifics(
  value: string,
  language: HonorificLanguage,
): string {
  const projected =
    language === "ar"
      ? upstreamArabicCompactions.reduce(
          (result, { source, target }) => result.replaceAll(source, target),
          value,
        )
      : value;
  return replaceAliases(projected, language, (entry) =>
    language === "en" ? entry.englishAliases : entry.arabicAliases,
  );
}

export function expandHonorifics(
  value: string,
  language: HonorificLanguage,
): string {
  return value.replace(honorificCharacterPattern, (character) => {
    const entry = byCharacter.get(character);
    if (!entry) return character;
    return language === "en" ? entry.accessibleEnglish : entry.expandedArabic;
  });
}

export function normalizeHonorificSearch(value: string): string {
  return honorificEntries
    .reduce((result, entry) => {
      const searchable = [
        entry.expandedArabic,
        entry.accessibleEnglish,
        ...entry.arabicAliases,
        ...entry.englishAliases,
      ].join(" ");
      const expanded = result.replaceAll(entry.compactCharacter, searchable);
      if (entry.alternateCharacters.length === 0) return expanded;
      return expanded.replace(
        new RegExp(entry.alternateCharacters.map(escapeRegExp).join("|"), "gu"),
        searchable,
      );
    }, value)
    .normalize("NFC")
    .toLocaleLowerCase();
}

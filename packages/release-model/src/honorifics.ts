import registry from "./honorifics.registry.json";

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

export const honorificRegistry = registry as {
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

export const honorificEntries = honorificRegistry.entries;

const byCharacter = new Map<string, HonorificEntry>();
for (const entry of honorificEntries) {
  byCharacter.set(entry.compactCharacter, entry);
  for (const alternate of entry.alternateCharacters) {
    byCharacter.set(alternate, entry);
  }
}

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
      language === "en" && entry.semanticClass === "divine-exaltation"
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
  return replaceAliases(value, language, (entry) =>
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

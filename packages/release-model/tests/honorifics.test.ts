import { describe, expect, it } from "vitest";

import {
  compactHonorifics,
  expandHonorifics,
  findHonorificByCharacter,
  alIsabahFormulaProjection,
  honorificEntries,
  normalizeHonorificSearch,
} from "../src/honorifics";

describe("honorific registry", () => {
  it("uses the pinned Al-Isabah formula projection without claiming policy ownership", () => {
    expect(alIsabahFormulaProjection.role).toBe("verified-consumer-projection");
    expect(alIsabahFormulaProjection.source).toMatchObject({
      repository: "https://github.com/yaqub0r/al-isabah",
      commit: "eb4fec9b744c12fcb677d9a7c53c4a58628aaa41",
      referenceVersion: "1.0.0",
      artifactVersion: "1.2.0",
    });

    const compactEntries = alIsabahFormulaProjection.entries.filter(
      ({ target }) => [...target].length === 1,
    );
    expect(compactEntries.length).toBeGreaterThan(0);
    for (const entry of compactEntries) {
      expect(findHonorificByCharacter(entry.target)).toMatchObject({
        semanticClass: entry.semanticClass,
      });
      expect(compactHonorifics(entry.source, "ar")).toBe(entry.target);
    }
  });

  it("models singular, dual, and plural companion agreement separately", () => {
    expect(findHonorificByCharacter("﵁")?.agreement).toEqual({
      number: "singular",
      gender: "masculine",
    });
    expect(findHonorificByCharacter("﵄")?.agreement.number).toBe("dual");
    expect(findHonorificByCharacter("﵅")?.agreement.gender).toBe("feminine");
  });

  it("uses the audited font only for supported compact characters", () => {
    expect(compactHonorifics("رضي الله عنهما", "ar")).toBe("﵄");
    expect(compactHonorifics("جل وعلا", "ar")).toBe("جل وعلا");
    expect(
      honorificEntries.find((entry) => entry.codePoint === "U+FBC3")
        ?.fontSupport,
    ).toBe("fallback-expanded");
    expect(compactHonorifics("may Allah Most High preserve them", "en")).toBe(
      "may Allah Most High preserve them",
    );
  });

  it("does not invent agreement when an English alias is ambiguous", () => {
    expect(compactHonorifics("may Allah be pleased with them", "en")).toBe(
      "may Allah be pleased with them",
    );
  });

  it("retains the divine name when compacting its exaltation", () => {
    expect(compactHonorifics("Allah Most High", "en")).toBe("Allah ﷾");
  });

  it("attaches compact honorifics without parenthetical commas", () => {
    expect(
      compactHonorifics(
        "the Prophet, may God bless him and grant him peace.",
        "en",
      ),
    ).toBe("the Prophet ﷺ.");
    expect(
      compactHonorifics(
        "the Prophet, may God bless him and grant him peace, said",
        "en",
      ),
    ).toBe("the Prophet ﷺ said");
    expect(
      compactHonorifics("May God bless him and grant him peace, he said", "en"),
    ).toBe("ﷺ, he said");
  });

  it("expands compact forms for each reading language", () => {
    expect(expandHonorifics("Abu Bakr ﵁", "en")).toBe(
      "Abu Bakr may Allah be pleased with him",
    );
    expect(expandHonorifics("أبو بكر ﵁", "ar")).toBe("أبو بكر رضي الله عنه");
  });

  it("makes compact forms searchable by their expanded meaning", () => {
    const indexed = normalizeHonorificSearch("Muhammad ﷺ");
    expect(indexed).toContain("may allah bless him and grant him peace");
    expect(indexed).toContain("صلى الله عليه وسلم");
  });
});

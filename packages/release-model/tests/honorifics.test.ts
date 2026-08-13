import { describe, expect, it } from "vitest";

import {
  compactHonorifics,
  expandHonorifics,
  findHonorificByCharacter,
  honorificEntries,
  normalizeHonorificSearch,
} from "../src/honorifics";

describe("honorific registry", () => {
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

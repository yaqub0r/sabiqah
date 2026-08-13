import {
  tokenizeHonorifics,
  type HonorificLanguage,
} from "@sabiqah/release-model";
import { Fragment } from "react";

export function HonorificText({
  text,
  language,
}: {
  text: string;
  language: HonorificLanguage;
}) {
  return tokenizeHonorifics(text).map((part, index) => {
    if (typeof part === "string") {
      return <Fragment key={`text-${index}`}>{part}</Fragment>;
    }
    const accessibleText =
      language === "en" ? part.accessibleEnglish : part.expandedArabic;
    return (
      <bdi
        className="honorific"
        dir="rtl"
        lang="ar"
        key={`${part.id}-${index}`}
      >
        <span
          aria-hidden="true"
          className="honorific-glyph"
          data-glyph={part.compactCharacter}
        />
        <span
          className="visually-hidden"
          dir={language === "en" ? "ltr" : "rtl"}
          lang={language}
        >
          {accessibleText}
        </span>
      </bdi>
    );
  });
}

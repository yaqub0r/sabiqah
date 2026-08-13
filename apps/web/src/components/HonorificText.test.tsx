// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HonorificText } from "./HonorificText";

describe("HonorificText", () => {
  it("shows the compact glyph while exposing expanded English to copy and assistive technology", () => {
    const { container } = render(
      <p>
        <HonorificText text="Muhammad ﷺ" language="en" />
      </p>,
    );

    expect(
      container.querySelector(".honorific-glyph")?.getAttribute("data-glyph"),
    ).toBe("ﷺ");
    expect(container.textContent).toBe(
      "Muhammad may Allah bless him and grant him peace",
    );
    expect(
      screen
        .getByText("may Allah bless him and grant him peace")
        .classList.contains("visually-hidden"),
    ).toBe(true);
  });

  it("exposes expanded Arabic when the reading language is Arabic", () => {
    const { container } = render(
      <p>
        <HonorificText text="محمد ﷺ" language="ar" />
      </p>,
    );

    expect(container.textContent).toBe("محمد صلى الله عليه وسلم");
  });

  it("leaves an expanded fallback untouched", () => {
    const { container } = render(
      <p>
        <HonorificText text="may Allah Most High preserve them" language="en" />
      </p>,
    );

    expect(container.querySelector(".honorific-glyph")).toBeNull();
    expect(container.textContent).toBe("may Allah Most High preserve them");
  });
});

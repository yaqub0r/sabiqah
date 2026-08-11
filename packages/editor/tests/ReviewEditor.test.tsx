// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import fixture from "../../../fixtures/releases/al-isabah-beta-v1.json";
import { parseBookRelease } from "@sabiqah/release-model";
import { ReviewEditor } from "../src";

const release = parseBookRelease(fixture);
const entry = release.entries[2];

afterEach(cleanup);

describe("ReviewEditor", () => {
  it("prepares a translation proposal without mutating canonical Arabic", () => {
    const onProposal = vi.fn();
    render(
      <ReviewEditor
        bookSlug={release.work.slug}
        baseReleaseId={release.release.id}
        entry={entry}
        onProposal={onProposal}
      />,
    );

    fireEvent.change(screen.getByLabelText("Proposed text"), {
      target: { value: "A revised synthetic translation." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Prepare proposal" }));

    expect(onProposal).toHaveBeenCalledOnce();
    expect(onProposal.mock.calls[0][0].operations[0]).toMatchObject({
      target: "translation",
      proposedText: "A revised synthetic translation.",
    });
    expect(entry.segments[0].arabic.text).toContain("موضع تجريبي");
  });

  it("requires rationale and evidence for protected Arabic corrections", () => {
    render(
      <ReviewEditor
        bookSlug={release.work.slug}
        baseReleaseId={release.release.id}
        entry={entry}
      />,
    );

    fireEvent.click(screen.getByLabelText("Protected Arabic correction"));
    fireEvent.click(screen.getByRole("button", { name: "Prepare proposal" }));

    expect(
      screen.getByText(/Arabic corrections require a rationale/),
    ).toBeTruthy();
  });
});

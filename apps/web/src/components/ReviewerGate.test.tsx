// @vitest-environment jsdom

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import fixture from "../../../../fixtures/releases/al-isabah-beta-v1.json";
import { parseBookRelease } from "@sabiqah/release-model";

import { ReviewerGate } from "./ReviewerGate";

const release = parseBookRelease(fixture);
const entry = release.entries[2];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ReviewerGate", () => {
  it("hydrates the authenticated review workspace as part of the same island", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          identity: {
            login: "beta-reviewer",
            avatarUrl: null,
            membershipStatus: "active",
          },
        }),
      }),
    );

    render(
      <ReviewerGate
        siteKey="test-site-key"
        returnTo="/admin/al-isabah/isabah-fixture-0003/"
        bookSlug={release.work.slug}
        releaseId={release.release.id}
        entry={entry}
      />,
    );

    await waitFor(() =>
      expect(screen.getByText("Reviewing as @beta-reviewer")).toBeTruthy(),
    );

    fireEvent.click(screen.getByLabelText("Protected Arabic correction"));

    expect(screen.getByLabelText("Rationale (required)")).toBeTruthy();
    expect(
      screen.getByLabelText("Evidence references, one per line (required)"),
    ).toBeTruthy();
  });
});

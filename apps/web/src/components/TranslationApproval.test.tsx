// @vitest-environment jsdom

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TranslationApproval } from "./TranslationApproval";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("TranslationApproval", () => {
  it("records approval for the displayed translation", async () => {
    const onChange = vi.fn();
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        state: {
          approvalCount: 1,
          currentUserApproved: true,
          latestApprovalAt: 1_765_000_000,
        },
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <TranslationApproval
        itemId="isabah-entry-00010759"
        onChange={onChange}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Approve this translation" }),
    );

    await waitFor(() => expect(onChange).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/corpus/al-isabah/reviews/isabah-entry-00010759",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ action: "approve" }),
      }),
    );
  });

  it("allows a reviewer to withdraw their current approval", async () => {
    let submittedBody: BodyInit | null | undefined;
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) => {
        submittedBody = init?.body;
        return {
          ok: true,
          json: async () => ({
            state: {
              approvalCount: 0,
              currentUserApproved: false,
              latestApprovalAt: null,
            },
          }),
        };
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <TranslationApproval
        itemId="isabah-entry-00010759"
        state={{
          approvalCount: 1,
          currentUserApproved: true,
          latestApprovalAt: 1_765_000_000,
        }}
        onChange={vi.fn()}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Withdraw my approval" }),
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(JSON.parse(submittedBody as string)).toEqual({
      action: "withdraw",
    });
  });
});

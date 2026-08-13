// @vitest-environment jsdom

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SelectionReporter } from "./SelectionReporter";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.getSelection()?.removeAllRanges();
  window.history.replaceState(null, "", "/");
});

function selectText(element: HTMLElement, start: number, end: number) {
  const range = document.createRange();
  range.setStart(element.firstChild!, start);
  range.setEnd(element.firstChild!, end);
  Object.defineProperty(range, "getBoundingClientRect", {
    value: () => ({
      left: 20,
      right: 120,
      top: 30,
      bottom: 48,
      width: 100,
      height: 18,
    }),
  });
  const selection = window.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(range);
  document.dispatchEvent(new Event("selectionchange"));
}

describe("SelectionReporter", () => {
  it("offers an accessible action and submits a structured report", async () => {
    window.history.replaceState(null, "", "/works/al-isabah/?volume=8#entry");
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) => ({
        ok: true,
        json: async () => ({
          issue: {
            number: 91,
            url: "https://github.com/yaqub0r/sabiqah/issues/91",
          },
        }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(
      <>
        <p
          data-report-item-id="isabah-entry-00011452"
          data-report-segment-id="isabah-entry-00011452-segment-1"
          data-report-field="segment"
          data-report-language="English"
        >
          Ibn Manda mentioned her, but he erred. Abu Nu'aym corrected him,
          explaining that she is Umm al-Dahhak, as she will appear correctly
          under the kunyahs.
        </p>
        <SelectionReporter corpusId="al-isabah-public-openiti-5835c18-v8" />
      </>,
    );

    selectText(screen.getByText(/Ibn Manda mentioned her/), 0, 18);
    fireEvent.click(
      await screen.findByRole("button", { name: "Report selected text" }),
    );
    expect(
      screen.getByRole("dialog", { name: "Report selected text" }),
    ).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Problem category"), {
      target: { value: "translation" },
    });
    fireEvent.change(screen.getByLabelText("What should a maintainer know?"), {
      target: { value: "Please compare this wording." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create issue" }));

    expect(
      await screen.findByRole("link", { name: "Open GitHub issue #91" }),
    ).toBeTruthy();
    const body = JSON.parse(
      String((fetchMock.mock.calls[0]![1] as RequestInit).body),
    );
    expect(body).toMatchObject({
      itemId: "isabah-entry-00011452",
      language: "English",
      category: "translation",
    });
  });

  it("keeps the native context menu without losing the selection action", async () => {
    render(
      <>
        <p
          data-report-item-id="isabah-entry-00011452"
          data-report-segment-id="isabah-entry-00011452-segment-1"
          data-report-field="segment"
          data-report-language="English"
        >
          This is public translated text for testing.
        </p>
        <SelectionReporter corpusId="al-isabah-public-openiti-5835c18-v8" />
      </>,
    );
    const paragraph = screen.getByText(/public translated/);
    selectText(paragraph, 8, 30);

    expect(
      await screen.findByRole("button", { name: "Report selected text" }),
    ).toBeTruthy();
    const event = new MouseEvent("contextmenu", {
      bubbles: true,
      cancelable: true,
      clientX: 60,
      clientY: 80,
    });
    paragraph.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(false);
    expect(
      screen.getByRole("button", { name: "Report selected text" }),
    ).toBeTruthy();
  });

  it("does not report a selection spanning two stable targets", async () => {
    render(
      <>
        <p
          data-report-item-id="one"
          data-report-segment-id="segment-one"
          data-report-field="segment"
          data-report-language="English"
        >
          First text
        </p>
        <p
          data-report-item-id="two"
          data-report-segment-id="segment-two"
          data-report-field="segment"
          data-report-language="English"
        >
          Second text
        </p>
        <SelectionReporter corpusId="corpus" />
      </>,
    );
    const paragraphs = screen.getAllByText(/text/);
    const range = document.createRange();
    range.setStart(paragraphs[0]!.firstChild!, 0);
    range.setEnd(paragraphs[1]!.firstChild!, 6);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    document.dispatchEvent(new Event("selectionchange"));
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Report selected text" }),
      ).toBeNull(),
    );
  });
});

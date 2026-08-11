import { JSDOM } from "jsdom";
import { describe, expect, it, vi } from "vitest";

import { decapMessage } from "../src/index";

describe("Decap OAuth callback", () => {
  it("completes Decap's two-step opener handshake", async () => {
    const origin = "https://dev.sabiqah.org";
    const opener = { postMessage: vi.fn() };
    const close = vi.fn();
    const response = decapMessage(origin, {
      token: "test-token",
      provider: "github",
    });
    const html = await response.text();
    const dom = new JSDOM(html, {
      runScripts: "dangerously",
      url: `${origin}/api/decap/callback`,
      beforeParse(window) {
        Object.defineProperty(window, "opener", { value: opener });
        window.close = close;
      },
    });

    expect(opener.postMessage).toHaveBeenCalledOnce();
    expect(opener.postMessage).toHaveBeenLastCalledWith(
      "authorizing:github",
      origin,
    );

    dom.window.dispatchEvent(
      new dom.window.MessageEvent("message", {
        data: "authorizing:github",
        origin: "https://attacker.example",
        source: opener as unknown as MessageEventSource,
      }),
    );
    expect(opener.postMessage).toHaveBeenCalledOnce();

    dom.window.dispatchEvent(
      new dom.window.MessageEvent("message", {
        data: "authorizing:github",
        origin,
        source: opener as unknown as MessageEventSource,
      }),
    );

    expect(opener.postMessage).toHaveBeenCalledTimes(2);
    expect(opener.postMessage).toHaveBeenLastCalledWith(
      'authorization:github:success:{"token":"test-token","provider":"github"}',
      origin,
    );
    expect(close).toHaveBeenCalledOnce();
  });
});

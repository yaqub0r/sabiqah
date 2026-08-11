import { describe, expect, it } from "vitest";

import {
  hmacHex,
  signPayload,
  timingSafeEqual,
  verifyPayload,
} from "../src/crypto";

describe("signed Worker state", () => {
  it("round-trips an authentic payload and rejects tampering", async () => {
    const token = await signPayload(
      { sub: "123", exp: 42 },
      "a-development-secret",
    );
    await expect(verifyPayload(token, "a-development-secret")).resolves.toEqual(
      { sub: "123", exp: 42 },
    );
    await expect(
      verifyPayload(`${token}x`, "a-development-secret"),
    ).resolves.toBeNull();
  });

  it("normalizes an invite to a stable digest before comparison", async () => {
    const first = await hmacHex("shared phrase", "pepper");
    const second = await hmacHex("shared phrase", "pepper");
    expect(timingSafeEqual(first, second)).toBe(true);
    expect(timingSafeEqual(first, `${second}0`)).toBe(false);
  });
});

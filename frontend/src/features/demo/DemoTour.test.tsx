import { describe, expect, it } from "vitest";
import { COMPARE, FEATURES } from "./features";

describe("demo tour content", () => {
  it("says the crawler and live data are not available online", () => {
    expect(FEATURES.find((f) => f.key === "crawler")?.status).toBe("local");
    expect(COMPARE.find(([k]) => k === "Job data")?.[1]).toMatch(/not updated in real time/);
    expect(COMPARE.find(([k]) => k === "Crawler")?.[1]).toMatch(/RAM.*paid hosting/);
  });
});

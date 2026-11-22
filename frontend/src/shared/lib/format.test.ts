import { describe, expect, it, vi, afterEach } from "vitest";
import { ago, label, money, parseQs, qs } from "./format";

afterEach(() => vi.useRealTimers());

describe("label", () => {
  it("prettifies snake_case and keeps known acronyms", () => {
    expect(label("technical_interview")).toBe("Technical interview");
    expect(label("devops")).toBe("DevOps");
    expect(label("ai_ml")).toBe("AI / ML");
  });
});

describe("ago", () => {
  it("handles today, yesterday, days, months and years", () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-06-15T12:00:00Z"));
    expect(ago("2026-06-15T01:00:00Z")).toBe("today");
    expect(ago("2026-06-14T01:00:00Z")).toBe("yesterday");
    expect(ago("2026-06-05T12:00:00Z")).toBe("10d ago");
    expect(ago("2026-03-15T12:00:00Z")).toBe("3mo ago");
    expect(ago("2024-06-15T12:00:00Z")).toBe("2y ago");
    expect(ago(null)).toBe("");
  });
});

describe("money", () => {
  it("formats euros and tolerates missing values", () => {
    expect(money(4800)).toContain("4");
    expect(money(undefined)).toBe("");
  });
});

describe("query strings", () => {
  it("drops empty values and repeats arrays", () => {
    expect(qs({ q: "python", city: ["Utrecht", "Delft"], x: "", y: [], z: null })).toBe("q=python&city=Utrecht&city=Delft");
  });
  it("round-trips through parseQs", () => {
    expect(parseQs("q=a&city=x&city=y")).toEqual({ q: "a", city: ["x", "y"] });
  });
});

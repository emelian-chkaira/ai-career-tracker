import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FitBadge, FitPanel, VERDICT, tone } from "./FitPanel";
import { mockApi, renderWith } from "@/test/utils";
import type { AiFit } from "@/shared/api/types";

vi.mock("@/features/auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u", email: "a@b.nl", role: "user", profile: {} } }) }));

const FIT: AiFit = { score: 82, verdict: "strong", reason: "Strong Python match.", strengths: ["Python APIs"], gaps: ["Kubernetes"], flags: ["Dutch required"], summary: "Build APIs.", model: "groq:gpt-oss", at: new Date().toISOString() };

describe("FitBadge", () => {
  it("shows score and verdict, or nothing", () => {
    const { container, rerender } = renderWith(<FitBadge ai={FIT} />);
    expect(screen.getByText(/AI 82 · Strong match/)).toBeInTheDocument();
    rerender(<FitBadge ai={null} />); expect(container).toBeEmptyDOMElement();
  });
  it("maps verdicts to tones", () => { expect(tone("strong")).toBe("ok"); expect(tone("stretch")).toBe("warn"); expect(tone("weak")).toBe("bad"); expect(VERDICT.good).toBe("Good match"); });
});

describe("FitPanel", () => {
  it("explains the evidence when a score exists", async () => {
    mockApi({ "GET /me/cv": { cv: {}, updated_at: "x" }, "GET /ai/settings": { provider: "ollama", model: "q", base_url: null, has_key: false } });
    renderWith(<FitPanel jobId={1} ai={FIT} />);
    expect(await screen.findByText("Why it fits")).toBeInTheDocument();
    expect(screen.getByText("Python APIs")).toBeInTheDocument(); expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    expect(screen.getByText(/Dutch required/)).toBeInTheDocument();
  });

  it("asks for a CV first, and disables scoring without one", async () => {
    mockApi({ "GET /me/cv": () => new Response(JSON.stringify({ detail: "no CV saved" }), { status: 404 }), "GET /ai/settings": { provider: "ollama", model: "q", base_url: null, has_key: false } });
    renderWith(<FitPanel jobId={1} ai={null} />);
    expect(await screen.findByText(/save your CV for AI scoring/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /score with ai/i })).toBeDisabled();
  });

  it("needs consent for an external model, then calls the API", async () => {
    const { calls } = mockApi({ "GET /me/cv": { cv: {}, updated_at: "x" }, "GET /ai/settings": { provider: "groq", model: "m", base_url: null, has_key: true }, "POST /me/fit/7": FIT });
    renderWith(<FitPanel jobId={7} ai={null} />);
    const btn = await screen.findByRole("button", { name: /score with ai/i });
    await waitFor(() => expect(btn).toBeDisabled());
    await userEvent.click(screen.getByRole("checkbox")); expect(btn).toBeEnabled();
    await userEvent.click(btn);
    await waitFor(() => expect(calls.find((c) => c.path === "/me/fit/7")?.body).toMatchObject({ consent: true }));
  });
});

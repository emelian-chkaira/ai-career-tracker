import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TailorPanel } from "./TailorPanel";
import { mockApi, renderWith } from "@/test/utils";

vi.mock("@/features/auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u", email: "a@b.nl", role: "user", profile: {} } }) }));
const COV = { matched: [], missing: [], percent: 50 };
const BASE = { latex: "x", template: "classic", cover_letter: null, model: "ollama:q", cv: {}, report: { before: COV, after: COV, changes: [], rejected: [], gaps: [], notes: "" } };
const AUTO = { on: false, stages: ["shortlisted"], push_rr: true, consent: false, available_stages: ["shortlisted", "applied"] };
const AI = { provider: "ollama", model: "q", base_url: null, has_key: false };

describe("TailorPanel", () => {
  it("tailors and rebuilds in Reactive Resume with one click", async () => {
    const { calls } = mockApi({ "GET /me/cv": { cv: {}, updated_at: "x" }, "GET /ai/settings": AI, "GET /me/rr": { connected: true }, "GET /me/tailor/auto": AUTO, "POST /me/tailor/7/rebuild": { ...BASE, report: { ...BASE.report, reactive_resume: { id: "r1", url: "https://rr/builder/r1", name: "CV - Dev @ Acme" } } } });
    renderWith(<TailorPanel jobId={7} title="Dev" />);
    await userEvent.click(await screen.findByRole("button", { name: "Tailor & rebuild in Reactive Resume" }));
    await vi.waitFor(() => expect(calls.find((c) => c.method === "POST" && c.path === "/me/tailor/7/rebuild")?.body).toMatchObject({ push: true }));
  });
  it("shows the Reactive Resume link of an already rebuilt CV and the automatic switch", async () => {
    mockApi({ "GET /me/cv": { cv: {}, updated_at: "x" }, "GET /ai/settings": AI, "GET /me/rr": { connected: true }, "GET /me/tailor/auto": AUTO, "GET /me/tailor/7": { ...BASE, report: { ...BASE.report, reactive_resume: { id: "r1", url: "https://rr/builder/r1", name: "CV - Dev @ Acme" } } } });
    renderWith(<TailorPanel jobId={7} title="Dev" />);
    expect(await screen.findByRole("link", { name: /Open it/ })).toHaveAttribute("href", "https://rr/builder/r1");
    expect(screen.getByLabelText(/Tailor automatically when I follow a job/)).not.toBeChecked();
  });
});

describe("TailorPanel match warning", () => {
  it("warns in plain words when the posting does not fit the CV", async () => {
    mockApi({ "GET /me/cv": { cv: {}, updated_at: "x" }, "GET /ai/settings": AI, "GET /me/rr": { connected: true }, "GET /me/tailor/auto": AUTO, "GET /me/tailor/7": { ...BASE, report: { ...BASE.report, poor_match: "Poor match: only 0% of this posting's requirements appear in your CV." } } });
    renderWith(<TailorPanel jobId={7} title="Dev" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Poor match: only 0%/);
  });
});

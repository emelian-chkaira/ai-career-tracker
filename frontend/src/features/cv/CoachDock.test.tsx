import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CoachDock } from "./CoachDock";
import { mockApi, renderWith } from "@/test/utils";

vi.mock("@/features/auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u", email: "a@b.nl", role: "user", profile: {} } }) }));
const AI = { provider: "ollama", model: "q", base_url: null, has_key: false };

describe("CoachDock", () => {
  it("turns what you say into an editable proposal and writes it to your CV only when you accept", async () => {
    const { calls } = mockApi({ "GET /ai/settings": AI, "GET /me/cv-coach/gaps/7": { missing: ["Kubernetes", "Terraform"] },
      "POST /me/cv-coach": { reply: "Added.", proposals: [{ kind: "skill", text: "Kubernetes" }] }, "POST /me/cv-coach/apply": { ok: true } });
    renderWith(<CoachDock jobId={7} title="Dev" onClose={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "Kubernetes" }));                      // a gap becomes a prompt
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    const box = await screen.findByLabelText("Edit Skill"); expect(box).toHaveValue("Kubernetes");
    expect(calls.some((c) => c.path === "/me/cv-coach/apply")).toBe(false);                               // nothing saved yet
    await userEvent.clear(box); await userEvent.type(box, "Kubernetes (EKS)");
    await userEvent.click(screen.getByRole("button", { name: "Add to my CV" }));
    await vi.waitFor(() => expect(calls.find((c) => c.path === "/me/cv-coach/apply")?.body).toMatchObject({ proposals: [{ kind: "skill", text: "Kubernetes (EKS)" }] }));
    expect(await screen.findByText(/Added to your CV/)).toBeInTheDocument();
  });
});

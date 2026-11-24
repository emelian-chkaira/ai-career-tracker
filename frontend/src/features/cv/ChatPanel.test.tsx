import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "./ChatPanel";
import { CvPicker } from "./CvPicker";
import { mockApi, renderWith } from "@/test/utils";

vi.mock("@/features/auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u", email: "a@b.nl", role: "user", profile: {} } }) }));
const AI = { provider: "ollama", model: "q", base_url: null, has_key: false };
const P0 = { folders: [] as string[], copyCv: () => {}, copyLetter: () => {} };
const CV = { name: "Sam", summary: "Backend developer", skills: ["Python"], experience: [] };

describe("ChatPanel", () => {
  it("shows the change for review and only edits the CV when you press Apply, and Undo puts it back", async () => {
    const { calls } = mockApi({ "GET /ai/settings": AI, "POST /me/cv-chat": { reply: "Shortened.", cv: { ...CV, summary: "Python dev" }, changes: [{ section: "Summary", title: "", before: "Backend developer", after: "Python dev" }] } });
    const applyCv = vi.fn();
    renderWith(<ChatPanel target="cv" docName="Main" folders={["Berlin"]} copyCv={() => {}} copyLetter={() => {}} cv={CV} letter="" jobId="" applyCv={applyCv} applyLetter={() => {}} />);
    await userEvent.type(await screen.findByLabelText("Message"), "shorter summary");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Python dev")).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/me/cv-chat")?.body).toMatchObject({ target: "cv", message: "shorter summary", cv: CV });
    expect(applyCv).not.toHaveBeenCalled();                                                               // nothing changed yet
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(applyCv).toHaveBeenLastCalledWith({ ...CV, summary: "Python dev" });
    await userEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(applyCv).toHaveBeenLastCalledWith(CV);
  });

  it("writes a cover letter into the letter editor only on Apply", async () => {
    mockApi({ "GET /ai/settings": AI, "POST /me/cv-chat": { reply: "Written.", letter: "Dear team," } });
    const applyLetter = vi.fn();
    renderWith(<ChatPanel {...P0} target="cover" docName="Letter" cv={CV} letter="" jobId="" applyCv={() => {}} applyLetter={applyLetter} />);
    await userEvent.type(await screen.findByLabelText("Message"), "write one");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await userEvent.click(await screen.findByRole("button", { name: "Apply" }));
    expect(applyLetter).toHaveBeenCalledWith("Dear team,");
  });

  it("can save the result as a new copy in a folder instead of changing the open CV", async () => {
    mockApi({ "GET /ai/settings": AI, "POST /me/cv-chat": { reply: "Done.", cv: { ...CV, summary: "Python dev" }, changes: [{ section: "Summary", title: "", before: "a", after: "Python dev" }] } });
    const applyCv = vi.fn(); const copyCv = vi.fn();
    renderWith(<ChatPanel target="cv" docName="Main" folders={["Berlin"]} copyCv={copyCv} copyLetter={() => {}} cv={CV} letter="" jobId="" applyCv={applyCv} applyLetter={() => {}} />);
    await userEvent.click(screen.getByLabelText(/Save as a new copy in/));
    await userEvent.selectOptions(screen.getByLabelText("Folder for the copy"), "Berlin");
    await userEvent.type(await screen.findByLabelText("Message"), "shorter");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await userEvent.click(await screen.findByRole("button", { name: "Save as copy" }));
    expect(copyCv).toHaveBeenCalledWith({ ...CV, summary: "Python dev" }, "Berlin");
    expect(applyCv).not.toHaveBeenCalled();
  });

  it("coming from a job it offers suggestions, and a gap suggestion waits for your detail instead of sending", async () => {
    const { calls } = mockApi({ "GET /ai/settings": AI, "POST /me/cv-chat/suggest/7": { job: { id: 7, title: "Dev", company: "Acme" }, suggestions: [
      { id: "summary", target: "cv", label: "Rewrite my summary for Dev", prompt: "Rewrite my summary" },
      { id: "gap-K", target: "cv", label: "I have used Kubernetes: add it", prompt: "I have used Kubernetes in my work. ", needs_detail: true }] } });
    renderWith(<ChatPanel target="cv" docName="Main" folders={["Berlin"]} copyCv={() => {}} copyLetter={() => {}} cv={CV} letter="" jobId="7" applyCv={() => {}} applyLetter={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "I have used Kubernetes: add it" }));
    expect(screen.getByLabelText("Message")).toHaveValue("I have used Kubernetes in my work. ");
    expect(calls.some((c) => c.path === "/me/cv-chat")).toBe(false);                                      // you must say where first
  });
});

describe("CvPicker", () => {
  const docs = [{ id: 1, kind: "cv", name: "Backend", is_default: true }, { id: 2, kind: "cv", name: "Mobile", is_default: false }];
  it("lets you choose which CV scores, and stays hidden with a single CV", async () => {
    mockApi({ "GET /me/docs": { docs } });
    const pick = vi.fn(); renderWith(<CvPicker value={null} onChange={pick} />);
    await userEvent.selectOptions(await screen.findByLabelText("CV used for AI scoring"), "2");
    expect(pick).toHaveBeenCalledWith(2);
  });
  it("renders nothing when there is only one CV", async () => {
    mockApi({ "GET /me/docs": { docs: [docs[0]] } });
    const { container } = renderWith(<CvPicker value={null} onChange={() => {}} />);
    await vi.waitFor(() => expect(container.querySelector("select")).toBeNull());
  });
});

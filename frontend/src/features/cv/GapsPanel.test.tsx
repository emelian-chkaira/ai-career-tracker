import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GapsPanel } from "./GapsPanel";
import { mockApi, renderWith } from "@/test/utils";

const RES = { target: "mobile", label: "Mobile / Flutter engineer", covered: ["Flutter"], tips: [{ id: "tip-github", text: "Add your GitHub link under Profiles." }],
  proposals: [{ id: "a", kind: "skill", section: "skills", term: "Agile", text: "Agile", why: "expected" }, { id: "b", kind: "experience", section: "experience", term: "CI/CD", text: "Automated releases with CI/CD.", why: "expected", index: 0, role: "Dev" }] };
const CV = { skills: ["Flutter"], experience: [{ title: "Dev", bullets: ["Built apps"] }], order: ["experience"] };

describe("GapsPanel", () => {
  it("pre-fills editable proposals and applies every accepted one in a single edit", async () => {
    mockApi({ "POST /cv/gaps": RES }); const edit = vi.fn();
    renderWith(<GapsPanel cv={CV} jobId="" edit={edit} />);
    await userEvent.click(screen.getByRole("button", { name: "Find gaps" }));
    expect(await screen.findByText(/Accept only what is true/)).toBeInTheDocument();
    const box = screen.getByLabelText("Edit CI/CD"); await userEvent.clear(box); await userEvent.type(box, "Shipped weekly releases via CI/CD.");
    expect(edit).not.toHaveBeenCalled();                                              // nothing changes until accepted
    await userEvent.click(screen.getByRole("button", { name: "Accept all 2" }));
    expect(edit).toHaveBeenCalledTimes(1);
    const patch = edit.mock.calls[0][0];
    expect(patch.skills).toEqual(["Flutter", "Agile"]);                               // the skill and the bullet are both in one patch
    expect(patch.experience[0].bullets).toEqual(["Built apps", "Shipped weekly releases via CI/CD."]);
  });
  it("skipping a proposal leaves the CV alone", async () => {
    mockApi({ "POST /cv/gaps": RES }); const edit = vi.fn();
    renderWith(<GapsPanel cv={CV} jobId="" edit={edit} />);
    await userEvent.click(screen.getByRole("button", { name: "Find gaps" }));
    await userEvent.click((await screen.findAllByRole("button", { name: "Skip" }))[0]);
    expect(edit).not.toHaveBeenCalled(); expect(screen.queryByLabelText("Edit Agile")).not.toBeInTheDocument();
  });
});

import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/shared/api/client";
import { renderWith } from "@/test/utils";
import { FirstRunGuide } from "./FirstRunGuide";

vi.mock("@/features/auth/AuthContext", () => ({ useAuth: () => ({ user: null, ready: true }) }));

describe("first-run guide", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("opens by itself on a fresh installation", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ google_client_id: null, first_run: true });
    renderWith(<FirstRunGuide />);
    expect(await screen.findByText("Welcome: set up your copy")).toBeTruthy();
  });

  it("stays closed once somebody has an account", async () => {
    const get = vi.spyOn(api, "get").mockResolvedValue({ google_client_id: null, first_run: false });
    renderWith(<FirstRunGuide />);
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(screen.queryByText("Welcome: set up your copy")).toBeNull();
  });
});

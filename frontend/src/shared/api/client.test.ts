import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, setAccessToken, setAuthLostHandler } from "./client";
import { mockApi } from "@/test/utils";

beforeEach(() => { setAccessToken(null); vi.restoreAllMocks(); });

describe("api client", () => {
  it("sends the bearer token and JSON bodies", async () => {
    setAccessToken("tok");
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await api.post("/x", { a: 1 });
    const init = spy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
    expect(init.body).toBe('{"a":1}');
  });

  it("turns error bodies into an ApiError with a readable message", async () => {
    mockApi({ "GET /boom": () => new Response(JSON.stringify({ detail: "no way" }), { status: 400 }), "GET /val": () => new Response(JSON.stringify({ detail: [{ msg: "bad a" }, { msg: "bad b" }] }), { status: 422 }) });
    await expect(api.get("/boom")).rejects.toMatchObject({ status: 400, message: "no way" });
    await expect(api.get("/val")).rejects.toMatchObject({ status: 422, message: "bad a; bad b" });
    await expect(api.get("/boom")).rejects.toBeInstanceOf(ApiError);
  });

  it("returns undefined on 204", async () => {
    mockApi({ "DELETE /thing": undefined });
    await expect(api.del("/thing")).resolves.toBeUndefined();
  });

  it("refreshes once on 401 and retries, or signals auth lost", async () => {
    const lost = vi.fn(); setAuthLostHandler(lost);
    let n = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const p = String(input);
      if (p.includes("/auth/refresh")) return new Response(JSON.stringify({ access_token: "new" }), { status: 200 });
      return n++ === 0 ? new Response("{}", { status: 401 }) : new Response(JSON.stringify({ ok: 1 }), { status: 200 });
    });
    await expect(api.get("/me/pipeline")).resolves.toEqual({ ok: 1 });
    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => (String(input).includes("/auth/refresh") ? new Response("{}", { status: 401 }) : new Response("{}", { status: 401 })));
    await expect(api.get("/me/pipeline")).rejects.toBeInstanceOf(ApiError);
    expect(lost).toHaveBeenCalled();
  });
});

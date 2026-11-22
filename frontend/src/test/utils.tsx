import { vi } from "vitest";
import { type ReactElement } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

/** Render with the providers the app uses: query cache (no retries) and a router. */
export function renderWith(ui: ReactElement, route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return { qc, ...render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter></QueryClientProvider>) };
}

/** Replace global fetch with a router of {"METHOD /path": body | (init)=>body}. Unknown routes answer 404. */
export function mockApi(routes: Record<string, unknown | ((init?: RequestInit) => unknown)>) {
  const calls: { method: string; path: string; body?: unknown }[] = [];
  const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const u = new URL(String(input), "http://localhost"); const method = (init?.method ?? "GET").toUpperCase();
    const key = `${method} ${u.pathname.replace(/^\/api\/v1/, "")}`;
    calls.push({ method, path: u.pathname.replace(/^\/api\/v1/, ""), body: init?.body ? JSON.parse(String(init.body)) : undefined });
    if (!(key in routes)) return new Response(JSON.stringify({ detail: "not found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    const v = routes[key]; const body = typeof v === "function" ? (v as (i?: RequestInit) => unknown)(init) : v;
    if (body instanceof Response) return body;
    return new Response(body === undefined ? null : JSON.stringify(body), { status: body === undefined ? 204 : 200, headers: { "Content-Type": "application/json" } });
  });
  return { calls, spy };
}

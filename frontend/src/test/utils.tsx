import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { App } from "../App";
import { ToastProvider } from "../components/Toasts";
import { adminUser } from "./fixtures";

type Handler = (body: unknown) => unknown;
export type Routes = Record<string, unknown | Handler>;

export const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });

/** Mock fetch with "METHOD /path" -> response (or handler) entries.
 * Signed in as an administrator unless ``GET /auth/me`` is overridden. */
export function mockApi(overrides: Routes) {
  const routes: Routes = { "GET /auth/me": adminUser, "GET /auth/status": { needs_setup: false }, ...overrides };
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input).replace(/^\/api\/v1/, "");
    const method = init?.method ?? "GET";
    const body =
      init?.body instanceof Blob ? init.body : init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path: url, body });
    const key = `${method} ${url}`;
    if (!(key in routes)) {
      return json({ detail: `No mock for ${key}` }, 404);
    }
    const entry = routes[key];
    const value = typeof entry === "function" ? (entry as Handler)(body) : entry;
    if (value instanceof Response) return value;
    return json(value, method === "POST" ? 201 : 200);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

export function renderApp(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { App } from "../App";
import { ToastProvider } from "../components/Toasts";

type Handler = (body: unknown) => unknown;
export type Routes = Record<string, unknown | Handler>;

/** Mock fetch with "METHOD /path" -> response (or handler) entries. */
export function mockApi(routes: Routes) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input).replace(/^\/api\/v1/, "");
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path: url, body });
    const key = `${method} ${url}`;
    if (!(key in routes)) {
      return new Response(JSON.stringify({ detail: `No mock for ${key}` }), { status: 404 });
    }
    const entry = routes[key];
    const value = typeof entry === "function" ? (entry as Handler)(body) : entry;
    if (value instanceof Response) return value;
    return new Response(JSON.stringify(value), { status: method === "POST" ? 201 : 200 });
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

import type { ConfigResponse, Row, RunDetail, RunSummary } from "./types";

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

type Detail = string | { loc?: (string | number)[]; msg: string }[] | undefined;

export function errorMessage(detail: Detail, status: number): string {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = (item.loc ?? []).filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join("\n");
  }
  if (typeof detail === "string") return detail;
  return `Request failed (${status})`;
}

export async function request<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const response = await fetch(API_BASE + path, {
    method: init.method ?? "GET",
    headers: init.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });

  if (response.status === 204) return undefined as T;

  const body = (await response.json().catch(() => null)) as { detail?: Detail } | null;

  if (!response.ok) {
    throw new ApiError(errorMessage(body?.detail, response.status), response.status);
  }

  return body as T;
}

export const api = {
  list: (path: string) => request<Row[]>(path),
  create: (path: string, body: Record<string, unknown>) => request<Row>(path, { method: "POST", body }),
  update: (path: string, id: number, body: Record<string, unknown>) =>
    request<Row>(`${path}/${id}`, { method: "PATCH", body }),
  remove: (path: string, id: number) => request<void>(`${path}/${id}`, { method: "DELETE" }),
  config: () => request<ConfigResponse>("/timetable/config"),
  runs: () => request<RunSummary[]>("/timetable/runs"),
  run: (id: string) => request<RunDetail>(`/timetable/runs/${id}`),
  startRun: (maxTimeSeconds: number) =>
    request<RunSummary>("/timetable/runs", { method: "POST", body: { max_time_seconds: maxTimeSeconds } }),
  fileUrl: (runId: string, name: string) => `${API_BASE}/timetable/runs/${runId}/files/${name}`,
};

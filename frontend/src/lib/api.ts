import type {
  ConfigResponse,
  CreatedAccount,
  CurrentUser,
  DataSummary,
  ImportResult,
  JsonSchema,
  Row,
  RunDetail,
  RunSummary,
  TimetableConfig,
} from "./types";

export const API_BASE = "/api/v1";
export const UNAUTHORIZED_EVENT = "timetable:unauthorized";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
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

interface RequestOptions {
  method?: string;
  body?: unknown;
  raw?: Blob;
}

export async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_BASE + path, {
      method: init.method ?? "GET",
      headers: init.raw
        ? { "Content-Type": "application/octet-stream" }
        : init.body !== undefined
          ? { "Content-Type": "application/json" }
          : undefined,
      body: init.raw ?? (init.body !== undefined ? JSON.stringify(init.body) : undefined),
    });
  } catch (error) {
    throw new ApiError(
      `Cannot reach the API server (${error instanceof Error ? error.message : String(error)}). ` +
        "Is the FastAPI backend running?",
      0,
    );
  }

  if (response.status === 401 && !path.startsWith("/auth/")) {
    // Session expired or signed out elsewhere: the AuthProvider shows the sign-in page.
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }

  if (response.status === 204) return undefined as T;

  const type = response.headers.get("content-type") ?? "";
  if (!type.includes("application/json")) {
    // e.g. the dev server returning index.html because /api is not proxied.
    throw new ApiError(
      `The API returned ${type || "no content type"} instead of JSON for ${path} (HTTP ${response.status}). ` +
        "Check that the FastAPI backend is running on port 8000 and restart the dev server " +
        "(npm run dev) so its /api proxy is active.",
      response.status,
    );
  }

  const body = (await response.json()) as { detail?: Detail } | null;

  if (!response.ok) {
    throw new ApiError(errorMessage(body?.detail, response.status), response.status, body?.detail);
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
  configSchema: () => request<JsonSchema>("/timetable/config/schema"),
  saveConfig: (config: TimetableConfig) => request<ConfigResponse>("/timetable/config", { method: "PUT", body: config }),
  resetConfig: () => request<ConfigResponse>("/timetable/config/reset", { method: "POST" }),

  runs: (status?: string) => request<RunSummary[]>(`/timetable/runs${status ? `?status_filter=${status}` : ""}`),
  run: (id: string) => request<RunDetail>(`/timetable/runs/${id}`),
  deleteRun: (id: string) => request<void>(`/timetable/runs/${id}`, { method: "DELETE" }),
  startRun: (maxTimeSeconds: number) =>
    request<RunSummary>("/timetable/runs", { method: "POST", body: { max_time_seconds: maxTimeSeconds } }),
  fileUrl: (runId: string, name: string) => `${API_BASE}/timetable/runs/${runId}/files/${name}`,

  pdfUrl: (runId: string, by: string, entities: string[] = [], download = false) => {
    const params = new URLSearchParams({ by });
    entities.forEach((entity) => params.append("entity", entity));
    if (download) params.set("download", "true");
    return `${API_BASE}/timetable/runs/${runId}/pdf?${params}`;
  },

  authStatus: () => request<{ needs_setup: boolean }>("/auth/status"),
  me: () => request<CurrentUser>("/auth/me"),
  login: (username: string, password: string) =>
    request<{ user: CurrentUser }>("/auth/login", { method: "POST", body: { username, password } }),
  setup: (body: { username: string; full_name: string; password: string }) =>
    request<{ user: CurrentUser }>("/auth/setup", { method: "POST", body }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  changePassword: (current_password: string, new_password: string) =>
    request<CurrentUser>("/auth/password", { method: "POST", body: { current_password, new_password } }),

  users: () => request<CurrentUser[]>("/users"),
  createUser: (body: Record<string, unknown>) => request<CurrentUser>("/users", { method: "POST", body }),
  updateUser: (id: number, body: Record<string, unknown>) =>
    request<CurrentUser>(`/users/${id}`, { method: "PATCH", body }),
  deleteUser: (id: number) => request<void>(`/users/${id}`, { method: "DELETE" }),
  createFacultyAccounts: () =>
    request<{ created: CreatedAccount[] }>("/users/faculty-accounts", { method: "POST" }),

  dataSummary: () => request<DataSummary>("/data/summary"),
  importData: (file: Blob) => request<ImportResult>("/data/import", { method: "POST", raw: file }),
  clearData: () => request<Record<string, number>>("/data/clear", { method: "POST" }),
  templateUrl: `${API_BASE}/data/template`,
  blankTemplateUrl: `${API_BASE}/data/template?blank=true`,
  sampleUrl: `${API_BASE}/data/sample`,
  exportUrl: `${API_BASE}/data/export`,
};

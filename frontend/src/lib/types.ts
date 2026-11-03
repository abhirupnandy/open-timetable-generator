// Shapes returned by the FastAPI backend (/api/v1).

export type Row = { id: number } & Record<string, unknown>;

export type RunStatus = "running" | "succeeded" | "failed";

export interface RunSummary {
  id: string;
  status: RunStatus;
  stage: string;
  started_at: string;
  finished_at: string | null;
  elapsed_seconds: number;
  max_time_seconds: number;
  session_count: number;
  solver_status: string | null;
  total_weighted_penalty: number | null;
  error: string | null;
}

export interface ScoreRow {
  key: string;
  constraint_id: string;
  mode: "off" | "soft" | "hard";
  weight: number;
  raw_penalty: number;
  weighted_penalty: number;
  solver_penalty: number | null;
  mismatch: boolean;
}

export interface ScoreReport {
  status: string;
  objective_value: number | null;
  best_bound: number | null;
  wall_time_seconds: number;
  build_time_seconds: number;
  model_stats: Record<string, number>;
  total_weighted_penalty: number;
  mismatches: string[];
  metrics: Record<string, number>;
  constraints: ScoreRow[];
}

export interface TimetableEntry {
  session_id: string;
  day: string;
  start_period: number;
  end_period: number;
  subject: string;
  course_code: string;
  group_code: string;
  group_name: string;
  faculty: string;
  /** Employee ID; missing in runs made before designations were recorded. */
  faculty_code?: string;
  faculty_designation?: string;
  course_name?: string;
  room: string | null;
}

export interface CalendarInfo {
  days: string[];
  periods: { number: number; start: string | null; end: string | null }[];
  lunch_after_period: number | null;
  blocked_slots?: BlockedSlot[];
  /** Enforced group blocks; a block applies to every group whose students overlap. */
  group_blocked_slots?: GroupBlockedSlot[];
}

export interface RunResult {
  /** "faculty" when the server returned only the signed-in faculty member's sessions. */
  scope?: "faculty";
  score_report: ScoreReport;
  validation: {
    is_valid: boolean;
    conflicts: number;
    violations: { reason: string; message: string }[];
  };
  diagnostics: string[];
  calendar: CalendarInfo;
  group_parents: Record<string, string | null>;
  entries: TimetableEntry[];
}

export interface RunDetail extends RunSummary {
  error_detail: string | null;
  log: string;
  files: { name: string; label: string }[];
  result: RunResult | null;
}

export interface GroupBlockedSlot {
  group_code: string;
  day: string;
  period: number;
  label: string;
}

export interface BlockedSlot {
  day: string;
  period: number;
  label: string;
}

export interface TimetableConfig {
  calendar: {
    days: string[];
    lunch_after_period: number | null;
    periods: { number: number; start: string; end: string }[];
    blocked_slots: BlockedSlot[];
  };
  solver: { max_time_seconds: number; workers: number; log_progress: boolean };
  hard: Record<string, { enabled: boolean } & Record<string, unknown>>;
  constraints: Record<string, { mode: "off" | "soft" | "hard"; weight: number } & Record<string, unknown>>;
  soft: Record<string, { enabled: boolean; weight: number } & Record<string, unknown>>;
}

export interface ConfigResponse {
  config: TimetableConfig;
  summary: string[];
  enabled_optional_hard_constraints: string[];
}

export type DataSummary = Record<string, number>;

export interface ImportIssue {
  sheet: string;
  row: number | null;
  column: string | null;
  message: string;
}

export interface ImportResult {
  ok: boolean;
  counts: Record<string, number>;
  issues: ImportIssue[];
}

/** Subset of JSON Schema produced by Pydantic's ``model_json_schema``. */
export interface JsonSchema {
  type?: string;
  title?: string;
  description?: string;
  enum?: unknown[];
  const?: unknown;
  default?: unknown;
  minimum?: number;
  exclusiveMinimum?: number;
  maximum?: number;
  items?: JsonSchema;
  properties?: Record<string, JsonSchema>;
  anyOf?: JsonSchema[];
  $ref?: string;
  $defs?: Record<string, JsonSchema>;
}

export type Role = "ADMIN" | "COORDINATOR" | "FACULTY";

export interface CurrentUser {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  faculty_employee_id: string | null;
  faculty: { employee_id: string; name: string; designation: string; designation_label: string } | null;
  is_active: boolean;
  last_login_at: string | null;
}

export interface CreatedAccount {
  username: string;
  full_name: string;
  email: string;
  password: string;
}

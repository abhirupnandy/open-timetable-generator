// Shapes returned by the FastAPI backend (/api/v1).

export type Row = { id: number } & Record<string, unknown>;

export type RunStatus = "running" | "succeeded" | "infeasible" | "failed";

export interface RunSummary {
  id: string;
  status: RunStatus;
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
  room: string | null;
}

export interface CalendarInfo {
  days: string[];
  periods: { number: number; start: string | null; end: string | null }[];
  lunch_after_period: number | null;
}

export interface RunResult {
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
  files: { name: string; label: string }[];
  result: RunResult | null;
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

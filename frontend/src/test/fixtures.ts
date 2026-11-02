import type { ConfigResponse, RunDetail, RunSummary } from "../lib/types";

export const schools = [{ id: 1, code: "SCI", name: "Science", is_active: true }];
export const rooms = [
  { id: 7, code: "LH-1", name: "Hall", room_type: "LECTURE_HALL", capacity: 100, school_id: 1, is_shared: false, is_active: true },
  { id: 8, code: "LAB-1", name: "Lab", room_type: "COMPUTER_LAB", capacity: 30, school_id: 1, is_shared: true, is_active: true },
];

export const config: ConfigResponse = {
  config: {
    calendar: {
      days: ["MONDAY", "TUESDAY"],
      lunch_after_period: 2,
      periods: [
        { number: 1, start: "08:00", end: "09:00" },
        { number: 2, start: "09:00", end: "10:00" },
        { number: 3, start: "11:00", end: "12:00" },
        { number: 4, start: "12:00", end: "13:00" },
      ],
      blocked_slots: [{ day: "MONDAY", period: 4, label: "TREP" }],
    },
    solver: { max_time_seconds: 120, workers: 8, log_progress: false },
    hard: { faculty_daily_span: { enabled: true, max_minutes: 480 } },
    constraints: { no_session_across_lunch: { mode: "soft", weight: 60 } },
    soft: { student_gaps: { enabled: true, weight: 100 }, faculty_compact_days: { enabled: false, weight: 15 } },
  },
  summary: [],
  enabled_optional_hard_constraints: ["faculty_daily_span"],
};

export const runSummary: RunSummary = {
  id: "run1",
  status: "succeeded",
  started_at: "2026-11-03T10:00:00+00:00",
  finished_at: "2026-11-03T10:00:20+00:00",
  elapsed_seconds: 20,
  max_time_seconds: 20,
  session_count: 3,
  solver_status: "OPTIMAL",
  total_weighted_penalty: 120,
  error: null,
};

export const runDetail: RunDetail = {
  ...runSummary,
  files: [{ name: "timetable_master.csv", label: "Master CSV" }],
  result: {
    score_report: {
      status: "OPTIMAL",
      objective_value: 120,
      best_bound: 120,
      wall_time_seconds: 1.5,
      build_time_seconds: 0.1,
      model_stats: { candidates: 40, variables: 90 },
      total_weighted_penalty: 120,
      mismatches: ["student_gaps"],
      metrics: { student_gaps: 1, sessions_across_lunch: 0 },
      constraints: [
        { key: "student_gaps", constraint_id: "S1", mode: "soft", weight: 100, raw_penalty: 1, weighted_penalty: 100, solver_penalty: 2, mismatch: true },
        { key: "faculty_compact_days", constraint_id: "", mode: "off", weight: 0, raw_penalty: 3, weighted_penalty: 0, solver_penalty: null, mismatch: false },
      ],
    },
    validation: { is_valid: true, conflicts: 0, violations: [] },
    diagnostics: [],
    calendar: {
      days: ["MONDAY", "TUESDAY"],
      lunch_after_period: 2,
      periods: [
        { number: 1, start: "08:00", end: "09:00" },
        { number: 2, start: "09:00", end: "10:00" },
        { number: 3, start: "11:00", end: "12:00" },
        { number: 4, start: "12:00", end: "13:00" },
      ],
    },
    group_parents: { G1: null, "G1-B1": "G1", "G1-B2": "G1" },
    entries: [
      { session_id: "a:1:s:1", day: "MONDAY", start_period: 1, end_period: 1, subject: "Maths", course_code: "C", group_code: "G1", group_name: "Group 1", faculty: "Dr A", room: "LH-1" },
      { session_id: "a:2:s:1", day: "MONDAY", start_period: 2, end_period: 3, subject: "Lab", course_code: "C", group_code: "G1-B1", group_name: "Batch 1", faculty: "Dr B", room: "LAB-1" },
      { session_id: "a:3:s:1", day: "TUESDAY", start_period: 3, end_period: 4, subject: "Physics", course_code: "C", group_code: "G1-B2", group_name: "Batch 2", faculty: "Dr A", room: null },
    ],
  },
};

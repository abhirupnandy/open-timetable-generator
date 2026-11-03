// Pure helpers for laying out the days x periods grid.
import { facultyLabel } from "./format";
import type { CalendarInfo, TimetableEntry } from "./types";

export type GridView = "group" | "faculty" | "room";

/** Stable faculty identifier: employee ID (older runs: the name). */
export const facultyKey = (entry: TimetableEntry) => entry.faculty_code || entry.faculty;

/** Faculty name with designation, e.g. "Dr A (Asst. Prof.)". */
export const entryFacultyLabel = (entry: TimetableEntry) => facultyLabel(entry.faculty, entry.faculty_designation);

export interface EntityOption {
  value: string;
  label: string;
}

/** Group codes whose students overlap with ``code``: itself, ancestors and descendants. */
export function relatedGroups(code: string, parents: Record<string, string | null>): Set<string> {
  const related = new Set([code]);

  let current = parents[code];
  while (current && !related.has(current)) {
    related.add(current);
    current = parents[current];
  }

  for (const other of Object.keys(parents)) {
    let ancestor = parents[other];
    const seen = new Set<string>();
    while (ancestor && !seen.has(ancestor)) {
      if (ancestor === code) {
        related.add(other);
        break;
      }
      seen.add(ancestor);
      ancestor = parents[ancestor];
    }
  }

  return related;
}

export function entriesFor(
  entries: TimetableEntry[],
  view: GridView,
  entity: string,
  parents: Record<string, string | null>,
): TimetableEntry[] {
  if (view === "group") {
    const related = relatedGroups(entity, parents);
    return entries.filter((entry) => related.has(entry.group_code));
  }
  if (view === "faculty") return entries.filter((entry) => facultyKey(entry) === entity);
  return entries.filter((entry) => entry.room === entity);
}

export function entityOptions(
  entries: TimetableEntry[],
  parents: Record<string, string | null>,
): Record<GridView, EntityOption[]> {
  const plain = (values: Iterable<string>) =>
    [...new Set(values)].sort((a, b) => a.localeCompare(b)).map((value) => ({ value, label: value }));

  const groupNames = new Map(entries.map((entry) => [entry.group_code, entry.group_name]));
  const faculty = new Map<string, EntityOption>();
  for (const entry of entries) {
    const key = facultyKey(entry);
    if (!faculty.has(key)) {
      const label = entryFacultyLabel(entry);
      faculty.set(key, { value: key, label: entry.faculty_code ? `${label} · ${entry.faculty_code}` : label });
    }
  }

  return {
    group: plain([...Object.keys(parents), ...entries.map((entry) => entry.group_code)]).map((option) => ({
      value: option.value,
      label: groupNames.get(option.value) ? `${option.value} · ${groupNames.get(option.value)}` : option.value,
    })),
    faculty: [...faculty.values()].sort((a, b) => a.label.localeCompare(b.label)),
    room: plain(entries.flatMap((entry) => (entry.room ? [entry.room] : []))),
  };
}

export type GridCell =
  | { kind: "sessions"; period: number; span: number; entries: TimetableEntry[] }
  | { kind: "blocked"; period: number; label: string }
  | { kind: "lunch" };

const covering = (entries: TimetableEntry[], day: string, period: number) =>
  entries.filter((entry) => entry.day === day && entry.start_period <= period && entry.end_period >= period);

const idsOf = (entries: TimetableEntry[]) =>
  entries
    .map((entry) => entry.session_id)
    .sort()
    .join("|");

/**
 * Cells for one day row. Consecutive periods holding the same sessions are
 * merged (e.g. a two-period lab) unless lunch falls between them.
 */
export function dayCells(
  entries: TimetableEntry[],
  day: string,
  calendar: CalendarInfo,
  blocked: { day: string; period: number; label: string }[],
): GridCell[] {
  const periods = calendar.periods.map((period) => period.number);
  const lunch = calendar.lunch_after_period;
  const cells: GridCell[] = [];

  let index = 0;
  while (index < periods.length) {
    const period = periods[index];
    const here = covering(entries, day, period);
    let span = 1;

    if (here.length) {
      while (index + span < periods.length && period + span - 1 !== lunch) {
        if (idsOf(covering(entries, day, period + span)) !== idsOf(here)) break;
        span += 1;
      }
    }

    const block = blocked.find((slot) => slot.day === day && slot.period === period);
    if (!here.length && block) cells.push({ kind: "blocked", period, label: block.label || "Blocked" });
    else cells.push({ kind: "sessions", period, span, entries: here });

    if (period + span - 1 === lunch) cells.push({ kind: "lunch" });
    index += span;
  }

  return cells;
}

import { DAYS } from "./format";
import type { Row } from "./types";

export const ENUMS: Record<string, string[]> = {
  designation: ["ASSISTANT_PROFESSOR", "ASSOCIATE_PROFESSOR", "PROFESSOR", "PHD_SCHOLAR"],
  time_preference: ["ANY", "MORNING", "AFTERNOON", "EVENING"],
  room_type: ["LECTURE_HALL", "COMPUTER_LAB", "SPECIAL_LAB", "CLASSROOM"],
  subject_type: ["LECTURE", "LAB", "TUTORIAL"],
  group_type: ["GROUP", "BATCH"],
  mode: ["IN_PERSON", "ONLINE", "EITHER"],
  day: DAYS,
  resource_type: ["FACULTY", "ROOM"],
};

export type ResourceKey =
  | "schools"
  | "courses"
  | "faculty"
  | "rooms"
  | "subjects"
  | "groups"
  | "assignments"
  | "unavailability"
  | "group-blocked-slots"
  | "session-locks";

export type FieldType = "text" | "email" | "int" | "bool" | "nullbool" | "enum" | "ref";

export interface Field {
  name: string;
  label?: string;
  type: FieldType;
  required?: boolean;
  nullable?: boolean;
  default?: unknown;
  /** Enum list name when it differs from the field name. */
  enumName?: string;
  /** Referenced resource, possibly depending on other form values. */
  ref?: ResourceKey | ((values: Record<string, unknown>) => ResourceKey);
  /** Field whose change resets this one. */
  dependsOn?: string;
  /** Cannot be changed after creation. */
  createOnly?: boolean;
  hint?: string;
}

export type RefData = Partial<Record<ResourceKey, Row[]>>;

export interface Resource {
  key: ResourceKey;
  label: string;
  singular: string;
  path: string;
  fields: Field[];
  columns: string[];
  display: (row: Row, refs: RefData) => string;
  /** Extra resources needed to label rows (beyond the form's ref fields). */
  extraRefs?: ResourceKey[];
}

const active: Field = { name: "is_active", label: "Active", type: "bool", default: true };

export function refLabel(refs: RefData, key: ResourceKey, id: unknown): string {
  if (id === null || id === undefined) return "";
  const row = refs[key]?.find((item) => item.id === id);
  if (!row) return `#${String(id)}`;
  return RESOURCES[key].display(row, refs);
}

const text = (row: Row, key: string) => String(row[key] ?? "");

export const RESOURCES: Record<ResourceKey, Resource> = {
  schools: {
    key: "schools",
    label: "Schools",
    singular: "school",
    path: "/schools",
    display: (row) => text(row, "code"),
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      active,
    ],
    columns: ["code", "name", "is_active"],
  },
  courses: {
    key: "courses",
    label: "Courses",
    singular: "course",
    path: "/courses",
    display: (row) => text(row, "code"),
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "school_id", label: "School", type: "ref", ref: "schools", required: true },
      { name: "duration_years", type: "int", required: true, default: 4 },
      { name: "total_semesters", type: "int", required: true, default: 8 },
      active,
    ],
    columns: ["code", "name", "school_id", "duration_years", "total_semesters", "is_active"],
  },
  faculty: {
    key: "faculty",
    label: "Faculty",
    singular: "faculty member",
    path: "/faculty",
    display: (row) => text(row, "name"),
    fields: [
      { name: "employee_id", label: "Employee ID", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "email", type: "email", required: true },
      { name: "designation", type: "enum", required: true },
      { name: "time_preference", type: "enum", default: "ANY" },
      {
        name: "preferred_day_off",
        type: "enum",
        enumName: "day",
        nullable: true,
        hint: "Used by the faculty_preferred_day_off soft constraint.",
      },
      { name: "school_id", label: "School", type: "ref", ref: "schools", required: true },
      active,
    ],
    columns: ["employee_id", "name", "designation", "time_preference", "preferred_day_off", "is_active"],
  },
  rooms: {
    key: "rooms",
    label: "Rooms",
    singular: "room",
    path: "/rooms",
    display: (row) => text(row, "code"),
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "room_type", type: "enum", required: true },
      { name: "capacity", type: "int", required: true },
      { name: "school_id", label: "School", type: "ref", ref: "schools", required: true },
      {
        name: "is_shared",
        label: "Shared room",
        type: "bool",
        default: false,
        hint: "Record external bookings as room unavailability.",
      },
      active,
    ],
    columns: ["code", "name", "room_type", "capacity", "is_shared", "is_active"],
  },
  subjects: {
    key: "subjects",
    label: "Subjects",
    singular: "subject",
    path: "/subjects",
    display: (row) => text(row, "code"),
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "subject_type", type: "enum", required: true },
      active,
    ],
    columns: ["code", "name", "subject_type", "is_active"],
  },
  groups: {
    key: "groups",
    label: "Groups & batches",
    singular: "group",
    path: "/groups",
    display: (row) => text(row, "code"),
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "group_type", type: "enum", required: true },
      { name: "course_id", label: "Course", type: "ref", ref: "courses", required: true },
      { name: "parent_group_id", label: "Parent group", type: "ref", ref: "groups", nullable: true },
      { name: "capacity", type: "int", nullable: true },
      active,
    ],
    columns: ["code", "name", "group_type", "course_id", "parent_group_id", "capacity", "is_active"],
  },
  assignments: {
    key: "assignments",
    label: "Teaching assignments",
    singular: "assignment",
    path: "/assignments",
    display: (row, refs) =>
      [
        refLabel(refs, "subjects", row.subject_id),
        refLabel(refs, "groups", row.academic_group_id),
        refLabel(refs, "faculty", row.faculty_id),
      ].join(" · "),
    fields: [
      { name: "subject_id", label: "Subject", type: "ref", ref: "subjects", required: true },
      { name: "course_id", label: "Course", type: "ref", ref: "courses", required: true },
      { name: "academic_group_id", label: "Group", type: "ref", ref: "groups", required: true },
      { name: "faculty_id", label: "Faculty", type: "ref", ref: "faculty", required: true },
      { name: "sessions_per_week", type: "int", required: true, default: 3 },
      { name: "duration_periods", type: "int", required: true, default: 1 },
      { name: "mode", type: "enum", required: true, default: "IN_PERSON" },
      { name: "required_room_type", type: "enum", enumName: "room_type", nullable: true },
      {
        name: "allow_across_lunch",
        type: "nullbool",
        hint: "Yes exempts this assignment from the lunch rule.",
      },
      active,
    ],
    columns: [
      "subject_id",
      "academic_group_id",
      "faculty_id",
      "sessions_per_week",
      "duration_periods",
      "mode",
      "required_room_type",
      "is_active",
    ],
  },
  unavailability: {
    key: "unavailability",
    label: "Unavailability",
    singular: "unavailability",
    path: "/unavailability",
    display: (row) => `${text(row, "resource_type")} ${text(row, "resource_id")} ${text(row, "day")}`,
    fields: [
      { name: "resource_type", type: "enum", required: true, createOnly: true, default: "FACULTY" },
      {
        name: "resource_id",
        label: "Faculty / room",
        type: "ref",
        ref: (values) => (values.resource_type === "ROOM" ? "rooms" : "faculty"),
        dependsOn: "resource_type",
        required: true,
        createOnly: true,
      },
      { name: "day", type: "enum", required: true },
      { name: "start_period", type: "int", required: true, default: 1 },
      { name: "end_period", type: "int", required: true, default: 1 },
      { name: "reason", type: "text", nullable: true },
    ],
    columns: ["resource_type", "resource_id", "day", "start_period", "end_period", "reason"],
    extraRefs: ["faculty", "rooms"],
  },
  "group-blocked-slots": {
    key: "group-blocked-slots",
    label: "Group blocked slots",
    singular: "blocked slot",
    path: "/group-blocked-slots",
    display: (row) => `${text(row, "day")} P${text(row, "period")}`,
    fields: [
      {
        name: "academic_group_id",
        label: "Group",
        type: "ref",
        ref: "groups",
        required: true,
        createOnly: true,
        hint: "Also applies to the group's batches.",
      },
      { name: "day", type: "enum", required: true },
      { name: "period", type: "int", required: true, default: 1 },
      { name: "label", type: "text", nullable: true },
    ],
    columns: ["academic_group_id", "day", "period", "label"],
  },
  "session-locks": {
    key: "session-locks",
    label: "Session locks",
    singular: "lock",
    path: "/session-locks",
    display: (row) => `${text(row, "day")} P${text(row, "start_period")}`,
    fields: [
      {
        name: "teaching_assignment_id",
        label: "Assignment",
        type: "ref",
        ref: "assignments",
        required: true,
        createOnly: true,
      },
      { name: "session_number", type: "int", required: true, default: 1, createOnly: true },
      { name: "day", type: "enum", required: true },
      { name: "start_period", type: "int", required: true, default: 1 },
      { name: "room_id", label: "Room (optional)", type: "ref", ref: "rooms", nullable: true },
    ],
    columns: ["teaching_assignment_id", "session_number", "day", "start_period", "room_id"],
    extraRefs: ["subjects", "groups", "faculty"],
  },
};

export const RESOURCE_KEYS = Object.keys(RESOURCES) as ResourceKey[];

export const fieldLabel = (field: Field) =>
  field.label ?? field.name.charAt(0).toUpperCase() + field.name.slice(1).replace(/_/g, " ");

export const enumOptions = (field: Field) => ENUMS[field.enumName ?? field.name] ?? [];

export function resolveRef(field: Field, values: Record<string, unknown>): ResourceKey | null {
  if (!field.ref) return null;
  return typeof field.ref === "function" ? field.ref(values) : field.ref;
}

/** Every resource whose rows are needed to label or edit ``resource``. */
export function refKeysFor(resource: Resource): ResourceKey[] {
  const keys = new Set<ResourceKey>(resource.extraRefs ?? []);
  for (const field of resource.fields) {
    if (field.type !== "ref" || !field.ref) continue;
    if (typeof field.ref === "function") {
      keys.add("faculty");
      keys.add("rooms");
    } else {
      keys.add(field.ref);
    }
  }
  for (const key of [...keys]) for (const extra of RESOURCES[key].extraRefs ?? []) keys.add(extra);
  if (keys.has("assignments")) ["subjects", "groups", "faculty"].forEach((key) => keys.add(key as ResourceKey));
  return [...keys];
}

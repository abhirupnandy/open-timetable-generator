export const DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];

/** "ASSISTANT_PROFESSOR" -> "Assistant professor" */
export function humanize(value: string): string {
  const text = value.toLowerCase().replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Stable hue (0-359) for colouring a subject consistently. */
export function hue(text: string): number {
  let hash = 0;
  for (const char of text) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash % 360;
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

const DESIGNATIONS: Record<string, string> = {
  PROFESSOR: "Prof.",
  ASSOCIATE_PROFESSOR: "Assoc. Prof.",
  ASSISTANT_PROFESSOR: "Asst. Prof.",
  PHD_SCHOLAR: "PhD Scholar",
};

/** "ASSISTANT_PROFESSOR" -> "Asst. Prof." */
export function designationLabel(designation: string | undefined | null): string {
  if (!designation) return "";
  return DESIGNATIONS[designation] ?? humanize(designation);
}

/** "Dr A (Asst. Prof.)", or just the name when the designation is unknown. */
export function facultyLabel(name: string, designation?: string | null): string {
  const label = designationLabel(designation);
  return label ? `${name} (${label})` : name;
}

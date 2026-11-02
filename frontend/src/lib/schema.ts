// Helpers for driving forms from Pydantic-generated JSON Schema.
import type { JsonSchema } from "./types";

export type Path = (string | number)[];

export interface Resolved {
  schema: JsonSchema;
  nullable: boolean;
}

/** Follow ``$ref`` and unwrap ``anyOf: [X, null]``. */
export function resolve(node: JsonSchema, root: JsonSchema): Resolved {
  if (node.$ref) {
    const name = node.$ref.replace("#/$defs/", "");
    const target = root.$defs?.[name] ?? {};
    const inner = resolve(target, root);
    return { schema: { ...inner.schema, default: node.default ?? inner.schema.default }, nullable: inner.nullable };
  }
  if (node.anyOf) {
    const options = node.anyOf.filter((option) => option.type !== "null");
    const nullable = options.length !== node.anyOf.length;
    const inner = resolve(options[0] ?? {}, root);
    return { schema: { ...inner.schema, default: node.default ?? inner.schema.default }, nullable: nullable || inner.nullable };
  }
  return { schema: node, nullable: false };
}

export type Kind = "boolean" | "integer" | "number" | "enum" | "string" | "array" | "object";

export function kindOf(schema: JsonSchema): Kind {
  if (schema.enum) return "enum";
  if (schema.type === "boolean") return "boolean";
  if (schema.type === "integer") return "integer";
  if (schema.type === "number") return "number";
  if (schema.type === "array") return "array";
  if (schema.type === "object" || schema.properties) return "object";
  return "string";
}

/** A sensible value for a new array row or a field that is switched on. */
export function emptyValue(node: JsonSchema, root: JsonSchema): unknown {
  const { schema, nullable } = resolve(node, root);
  if (schema.default !== undefined) return structuredClone(schema.default);
  if (nullable) return null;
  switch (kindOf(schema)) {
    case "boolean":
      return false;
    case "integer":
    case "number":
      return schema.minimum ?? (schema.exclusiveMinimum !== undefined ? schema.exclusiveMinimum + 1 : 0);
    case "enum":
      return schema.enum?.[0] ?? "";
    case "array":
      return [];
    case "object":
      return Object.fromEntries(
        Object.entries(schema.properties ?? {}).map(([key, child]) => [key, emptyValue(child, root)]),
      );
    default:
      return "";
  }
}

export function getIn(value: unknown, path: Path): unknown {
  return path.reduce<unknown>((current, key) => (current as Record<string | number, unknown> | undefined)?.[key], value);
}

/** Immutable set: returns a copy of ``value`` with ``path`` replaced. */
export function setIn<T>(value: T, path: Path, next: unknown): T {
  if (!path.length) return next as T;
  const [head, ...rest] = path;
  const container = (value ?? (typeof head === "number" ? [] : {})) as Record<string | number, unknown>;
  const copy = (Array.isArray(container) ? [...container] : { ...container }) as Record<string | number, unknown>;
  copy[head] = setIn(container[head], rest, next);
  return copy as T;
}

export const pathKey = (path: Path) => path.join(".");

/** Parse "1, 2, 3" into numbers, ignoring blanks. Returns null on invalid input. */
export function parseNumberList(text: string): number[] | null {
  const parts = text.split(/[,\s]+/).filter(Boolean);
  const numbers = parts.map(Number);
  return numbers.every((number) => Number.isInteger(number)) ? numbers : null;
}

export function label(key: string | number): string {
  const text = String(key).replace(/_/g, " ");
  return /^[A-Z_ ]+$/.test(String(key)) ? text.charAt(0) + text.slice(1).toLowerCase() : text.charAt(0).toUpperCase() + text.slice(1);
}
